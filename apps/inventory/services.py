import uuid
import logging
from django.db import transaction, models
from django.core.cache import cache
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.products.models import Product
from apps.warehouses.models import Warehouse
from apps.accounts.models import User
from core.exceptions import ResourceNotFoundException, InsufficientInventoryException
from core.constants import INVENTORY_LOW_STOCK_CACHE_TTL

logger = logging.getLogger(__name__)

def adjust_inventory(data: dict, performed_by_user_id: int) -> InventoryTransaction:
    product_id = data['product_id']
    warehouse_id = data['warehouse_id']
    transaction_type = data['transaction_type']
    quantity = data['quantity']
    notes = data.get('notes', '')

    try:
        user = User.objects.get(id=performed_by_user_id)
    except User.DoesNotExist:
        raise ResourceNotFoundException("User not found.")

    with transaction.atomic():
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ResourceNotFoundException("Product not found.")

        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            raise ResourceNotFoundException("Warehouse not found.")

        # Lock row for safety using select_for_update
        inventory, created = Inventory.objects.select_for_update().get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={'quantity_available': 0, 'quantity_reserved': 0, 'quantity_damaged': 0}
        )

        qty = int(quantity)
        if transaction_type == TransactionType.INBOUND:
            inventory.quantity_available += qty
        elif transaction_type == TransactionType.OUTBOUND:
            if inventory.quantity_available < qty:
                raise InsufficientInventoryException(
                    detail=f"Insufficient inventory. Available: {inventory.quantity_available}, Required: {qty}",
                    code="INSUFFICIENT_INVENTORY"
                )
            inventory.quantity_available -= qty
        elif transaction_type == TransactionType.DAMAGE_REPORT:
            if inventory.quantity_available < qty:
                raise InsufficientInventoryException(
                    detail=f"Insufficient inventory to mark as damaged. Available: {inventory.quantity_available}, Required: {qty}",
                    code="INSUFFICIENT_INVENTORY"
                )
            inventory.quantity_available -= qty
            inventory.quantity_damaged += qty
        elif transaction_type == TransactionType.ADJUSTMENT:
            # Resulting quantity available cannot be negative
            new_avail = inventory.quantity_available + qty
            if new_avail < 0:
                raise InsufficientInventoryException(
                    detail=f"Adjustment would result in negative inventory: {new_avail}",
                    code="INSUFFICIENT_INVENTORY"
                )
            inventory.quantity_available = new_avail

        inventory.save()

        # Create Inventory Transaction
        tx = InventoryTransaction.objects.create(
            product=product,
            warehouse=warehouse,
            transaction_type=transaction_type,
            quantity=qty,
            performed_by=user,
            notes=notes
        )

        # Trigger background Celery tasks after transaction commits
        from apps.inventory.tasks import process_inventory_updated_event
        transaction.on_commit(
            lambda: process_inventory_updated_event.delay(product.id, warehouse.id, transaction_type, qty)
        )
        
        # Invalidate low stock cache key
        cache.delete('inventory:low-stock')

        return tx

def transfer_inventory(data: dict, performed_by_user_id: int) -> dict:
    product_id = data['product_id']
    source_warehouse_id = data['source_warehouse_id']
    destination_warehouse_id = data['destination_warehouse_id']
    quantity = int(data['quantity'])
    notes = data.get('notes', '')

    try:
        user = User.objects.get(id=performed_by_user_id)
    except User.DoesNotExist:
        raise ResourceNotFoundException("User not found.")

    # Shared reference ID
    transfer_ref = f"TRANSFER-{str(uuid.uuid4())[:8].upper()}"

    with transaction.atomic():
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ResourceNotFoundException("Product not found.")

        try:
            source_wh = Warehouse.objects.get(id=source_warehouse_id)
            dest_wh = Warehouse.objects.get(id=destination_warehouse_id)
        except Warehouse.DoesNotExist:
            raise ResourceNotFoundException("Warehouse not found.")

        # Avoid deadlocks by sorting the warehouse IDs and locking rows consistently
        sorted_wh_ids = sorted([source_warehouse_id, destination_warehouse_id])
        
        inventory_map = {}
        for wh_id in sorted_wh_ids:
            wh = source_wh if wh_id == source_warehouse_id else dest_wh
            inv, _ = Inventory.objects.select_for_update().get_or_create(
                product=product,
                warehouse=wh,
                defaults={'quantity_available': 0, 'quantity_reserved': 0, 'quantity_damaged': 0}
            )
            inventory_map[wh_id] = inv

        source_inv = inventory_map[source_warehouse_id]
        dest_inv = inventory_map[destination_warehouse_id]

        if source_inv.quantity_available < quantity:
            raise InsufficientInventoryException(
                detail=f"Source warehouse has insufficient inventory. Available: {source_inv.quantity_available}, Required: {quantity}",
                code="INSUFFICIENT_INVENTORY"
            )

        # Update quantities
        source_inv.quantity_available -= quantity
        dest_inv.quantity_available += quantity

        source_inv.save()
        dest_inv.save()

        # Create OUTBOUND transaction for source
        tx_out = InventoryTransaction.objects.create(
            product=product,
            warehouse=source_wh,
            transaction_type=TransactionType.OUTBOUND,
            quantity=quantity,
            reference_id=transfer_ref,
            performed_by=user,
            notes=f"Transfer to {dest_wh.warehouse_code}. {notes}"
        )

        # Create INBOUND transaction for destination
        tx_in = InventoryTransaction.objects.create(
            product=product,
            warehouse=dest_wh,
            transaction_type=TransactionType.INBOUND,
            quantity=quantity,
            reference_id=transfer_ref,
            performed_by=user,
            notes=f"Transfer from {source_wh.warehouse_code}. {notes}"
        )

        # Dispatch Celery tasks after transaction commits
        from apps.inventory.tasks import process_inventory_transfer_event
        transaction.on_commit(
            lambda: process_inventory_transfer_event.delay(product.id, source_warehouse_id, destination_warehouse_id, quantity)
        )
        
        # Invalidate low stock cache key
        cache.delete('inventory:low-stock')

        return {
            "reference_id": transfer_ref,
            "source_transaction_id": tx_out.id,
            "destination_transaction_id": tx_in.id,
            "quantity_transferred": quantity
        }

def get_low_stock_alerts() -> list:
    cache_key = 'inventory:low-stock'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Query all active inventory records where available stock <= product reorder level
    low_stock_records = Inventory.objects.select_related('product', 'warehouse').filter(
        quantity_available__lte=models.F('product__reorder_level'),
        product__is_active=True,
        warehouse__is_active=True
    )

    alerts = []
    for record in low_stock_records:
        deficit = record.product.reorder_level - record.quantity_available
        alerts.append({
            "product_id": record.product.id,
            "sku": record.product.sku,
            "product_name": record.product.name,
            "warehouse_id": record.warehouse.id,
            "warehouse_name": record.warehouse.name,
            "quantity_available": record.quantity_available,
            "reorder_level": record.product.reorder_level,
            "deficit": deficit
        })

    cache.set(cache_key, alerts, timeout=INVENTORY_LOW_STOCK_CACHE_TTL)
    return alerts

def check_and_publish_low_stock_alert(product_id: int, warehouse_id: int) -> None:
    try:
        record = Inventory.objects.select_related('product', 'warehouse').get(
            product_id=product_id,
            warehouse_id=warehouse_id
        )
    except Inventory.DoesNotExist:
        return

    if record.quantity_available <= record.product.reorder_level:
        logger.warning(
            f"LOW STOCK ALERT: Product {record.product.sku} in Warehouse {record.warehouse.warehouse_code} "
            f"has {record.quantity_available} units remaining (reorder level: {record.product.reorder_level})"
        )
        
        # Invalidate low-stock Redis cache key
        cache.delete('inventory:low-stock')
