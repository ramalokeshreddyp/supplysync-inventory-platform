import datetime
import uuid
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from apps.sales_orders.models import SalesOrder, SalesOrderItem, SalesOrderStatus
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from apps.accounts.models import User
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from core.exceptions import ResourceNotFoundException, InsufficientInventoryException, InvalidOperationException

def _generate_so_number() -> str:
    today_str = datetime.date.today().strftime("%Y%m%d")
    random_str = str(uuid.uuid4())[:6].upper()
    return f"SO-{today_str}-{random_str}"

def create_sales_order(data: dict, created_by_user_id: int) -> SalesOrder:
    warehouse_id = data['warehouse_id']
    customer_name = data['customer_name']
    customer_email = data['customer_email']
    customer_phone = data['customer_phone']
    shipping_address = data['shipping_address']
    notes = data.get('notes')
    items_data = data.get('items', [])

    try:
        creator = User.objects.get(id=created_by_user_id)
    except User.DoesNotExist:
        raise ResourceNotFoundException("Creator user not found.")

    with transaction.atomic():
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            raise ResourceNotFoundException("Warehouse not found.")

        # Avoid deadlocks by sorting products if locking them
        # Let's collect item information
        product_ids = [item['product_id'] for item in items_data]
        products = Product.objects.in_bulk(product_ids)
        
        # Sort items by product ID for consistent locking order
        sorted_items = sorted(items_data, key=lambda x: x['product_id'])

        # Stock check and row locking
        short_items = []
        inventory_to_lock = []
        for item in sorted_items:
            prod_id = item['product_id']
            qty = int(item['quantity'])
            
            product = products.get(prod_id)
            if not product:
                raise ResourceNotFoundException(f"Product ID {prod_id} not found.")

            # select_for_update to lock the row
            inv, _ = Inventory.objects.select_for_update().get_or_create(
                product=product,
                warehouse=warehouse,
                defaults={'quantity_available': 0, 'quantity_reserved': 0, 'quantity_damaged': 0}
            )
            
            if inv.quantity_available < qty:
                short_items.append({
                    "sku": product.sku,
                    "requested_quantity": qty,
                    "available_quantity": inv.quantity_available
                })
            else:
                inventory_to_lock.append((inv, qty))

        # If any item is short, roll back and raise error
        if short_items:
            raise InsufficientInventoryException(
                detail={
                    "message": "Insufficient stock for order.",
                    "short_items": short_items
                },
                code="INSUFFICIENT_STOCK_FOR_ORDER"
            )

        # Generate SO Number
        order_number = _generate_so_number()
        while SalesOrder.all_objects.filter(order_number=order_number).exists():
            order_number = _generate_so_number()

        so = SalesOrder.objects.create(
            order_number=order_number,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            shipping_address=shipping_address,
            warehouse=warehouse,
            status=SalesOrderStatus.CONFIRMED,  # Creates order in CONFIRMED status
            created_by=creator,
            notes=notes
        )

        total_amount = 0
        # Reserve inventory and create items
        for inv, qty in inventory_to_lock:
            # increase quantity_reserved and decrease quantity_available
            inv.quantity_available -= qty
            inv.quantity_reserved += qty
            inv.save()

            so_item = SalesOrderItem.objects.create(
                sales_order=so,
                product=inv.product,
                quantity=qty,
                unit_price=inv.product.unit_price,
                total_price=qty * inv.product.unit_price
            )
            total_amount += so_item.total_price

        so.total_amount = total_amount
        so.save()

        # Invalidate low stock cache key
        cache.delete('inventory:low-stock')

        # Dispatch Celery task
        from apps.sales_orders.tasks import process_sales_order_created_event
        transaction.on_commit(
            lambda: process_sales_order_created_event.delay(so.id, created_by_user_id)
        )

        return so

def dispatch_sales_order(so_id: int) -> SalesOrder:
    try:
        so = SalesOrder.objects.get(id=so_id)
    except SalesOrder.DoesNotExist:
        raise ResourceNotFoundException("Sales Order not found.")

    if so.status != SalesOrderStatus.CONFIRMED:
        raise InvalidOperationException(
            detail=f"Only CONFIRMED sales orders can be dispatched. Current status: {so.status}",
            code="INVALID_OPERATION"
        )

    with transaction.atomic():
        # Sort items by product ID to avoid deadlocks during lock acquisition
        items = sorted(so.items.all(), key=lambda x: x.product.id)
        
        for item in items:
            # Lock the inventory record
            inv = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=so.warehouse
            )
            
            # Decrease quantity_reserved (physical stock leaves)
            inv.quantity_reserved -= item.quantity
            inv.save()

            # Create OUTBOUND transaction
            InventoryTransaction.objects.create(
                product=item.product,
                warehouse=so.warehouse,
                transaction_type=TransactionType.OUTBOUND,
                performed_by=so.created_by,
                quantity=item.quantity,
                reference_id=so.order_number,
                notes=f"Dispatch for order {so.order_number}"
            )

        so.status = SalesOrderStatus.DISPATCHED
        so.dispatched_at = timezone.now()
        so.save()
        return so

def deliver_sales_order(so_id: int) -> SalesOrder:
    try:
        so = SalesOrder.objects.get(id=so_id)
    except SalesOrder.DoesNotExist:
        raise ResourceNotFoundException("Sales Order not found.")

    if so.status != SalesOrderStatus.DISPATCHED:
        raise InvalidOperationException(
            detail=f"Only DISPATCHED sales orders can be delivered. Current status: {so.status}",
            code="INVALID_OPERATION"
        )

    so.status = SalesOrderStatus.DELIVERED
    so.delivered_at = timezone.now()
    so.save()
    return so

def cancel_sales_order(so_id: int, reason: str) -> SalesOrder:
    try:
        so = SalesOrder.objects.get(id=so_id)
    except SalesOrder.DoesNotExist:
        raise ResourceNotFoundException("Sales Order not found.")

    # Only PENDING and CONFIRMED orders can be cancelled
    if so.status not in [SalesOrderStatus.PENDING, SalesOrderStatus.CONFIRMED]:
        raise InvalidOperationException(
            detail=f"Orders with status {so.status} cannot be cancelled.",
            code="INVALID_OPERATION"
        )

    with transaction.atomic():
        # Sort items by product ID to avoid deadlocks during lock acquisition
        items = sorted(so.items.all(), key=lambda x: x.product.id)
        
        for item in items:
            # Lock the inventory record
            inv = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=so.warehouse
            )
            
            # Release reserved inventory
            inv.quantity_reserved -= item.quantity
            inv.quantity_available += item.quantity
            inv.save()

        so.status = SalesOrderStatus.CANCELLED
        if reason:
            so.notes = f"{so.notes or ''}\nCancellation Reason: {reason}".strip()
        so.save()

        # Invalidate low stock cache key
        cache.delete('inventory:low-stock')

        # Dispatch Celery task
        from apps.sales_orders.tasks import process_sales_order_cancelled_event
        transaction.on_commit(
            lambda: process_sales_order_cancelled_event.delay(so.id)
        )

        return so
