import datetime
from django.db import transaction
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from apps.suppliers.models import Supplier
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from apps.accounts.models import User, UserRole
from apps.inventory.services import adjust_inventory
from core.exceptions import ResourceNotFoundException, InvalidOperationException

def _generate_po_number() -> str:
    today_str = datetime.date.today().strftime("%Y%m%d")
    key = f"po-sequence:{today_str}"
    
    # Atomic increment with Redis (via Django cache interface)
    is_new = cache.add(key, 1, timeout=86400)
    if is_new:
        seq = 1
    else:
        try:
            seq = cache.incr(key)
        except ValueError:
            # Fallback if increment fails
            seq = 1
            cache.set(key, 1, timeout=86400)
            
    return f"PO-{today_str}-{seq:04d}"

def create_purchase_order(data: dict, created_by_user_id: int) -> PurchaseOrder:
    supplier_id = data['supplier_id']
    warehouse_id = data['warehouse_id']
    expected_delivery_date = data.get('expected_delivery_date')
    notes = data.get('notes')
    items_data = data.get('items', [])

    try:
        creator = User.objects.get(id=created_by_user_id)
    except User.DoesNotExist:
        raise ResourceNotFoundException("Creator user not found.")

    with transaction.atomic():
        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            raise ResourceNotFoundException("Supplier not found.")

        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            raise ResourceNotFoundException("Warehouse not found.")

        po_number = _generate_po_number()

        po = PurchaseOrder.objects.create(
            po_number=po_number,
            supplier=supplier,
            warehouse=warehouse,
            expected_delivery_date=expected_delivery_date,
            notes=notes,
            created_by=creator,
            status=PurchaseOrderStatus.DRAFT
        )

        total_amount = 0
        for item in items_data:
            try:
                product = Product.objects.get(id=item['product_id'])
            except Product.DoesNotExist:
                raise ResourceNotFoundException(f"Product ID {item['product_id']} not found.")

            qty_ordered = int(item['quantity_ordered'])
            unit_price = float(item['unit_price'])
            
            po_item = PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=product,
                quantity_ordered=qty_ordered,
                unit_price=unit_price,
                total_price=qty_ordered * unit_price
            )
            total_amount += po_item.total_price

        po.total_amount = total_amount
        po.save()
        return po

def submit_purchase_order(po_id: int) -> PurchaseOrder:
    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase Order not found.")

    if po.status != PurchaseOrderStatus.DRAFT:
        raise InvalidOperationException(
            detail=f"Only DRAFT purchase orders can be submitted. Current status: {po.status}",
            code="INVALID_OPERATION"
        )

    # Validate that PO has at least one item before submission
    if not po.items.exists():
        raise InvalidOperationException(
            detail="Purchase order must have at least one item to submit.",
            code="PO_HAS_NO_ITEMS"
        )

    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    po.save()
    return po

def approve_purchase_order(po_id: int, approved_by_user_id: int) -> PurchaseOrder:
    try:
        approver = User.objects.get(id=approved_by_user_id)
    except User.DoesNotExist:
        raise ResourceNotFoundException("Approver not found.")

    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase Order not found.")

    if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise InvalidOperationException(
            detail=f"Only PENDING_APPROVAL purchase orders can be approved. Current status: {po.status}",
            code="INVALID_OPERATION"
        )

    # A PO cannot be approved by the same user who created it
    if po.created_by == approver:
        raise PermissionDenied(
            detail="A purchase order cannot be approved by the same user who created it.",
            code="SELF_APPROVAL_NOT_ALLOWED"
        )

    # Moves the PO from PENDING_APPROVAL to APPROVED
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by = approver
    po.save()
    return po

def receive_purchase_order(po_id: int, data: dict, performed_by_user_id: int) -> PurchaseOrder:
    items_received = data.get('items', [])
    actual_delivery_date = data.get('actual_delivery_date')

    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase Order not found.")

    # PO status must be APPROVED or ORDERED or PARTIALLY_RECEIVED to receive goods
    # If in DRAFT or PENDING_APPROVAL or CANCELLED, raise InvalidOperationException
    if po.status in [PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING_APPROVAL, PurchaseOrderStatus.CANCELLED, PurchaseOrderStatus.RECEIVED]:
        raise InvalidOperationException(
            detail=f"Goods cannot be received for purchase orders with status: {po.status}",
            code="INVALID_OPERATION"
        )

    with transaction.atomic():
        for item_data in items_received:
            po_item_id = item_data['po_item_id']
            qty_received = int(item_data['quantity_received'])

            try:
                po_item = PurchaseOrderItem.objects.get(id=po_item_id, purchase_order=po)
            except PurchaseOrderItem.DoesNotExist:
                raise ResourceNotFoundException(f"Purchase order item {po_item_id} not found on this PO.")

            # quantity_received cannot exceed quantity_ordered minus already received
            max_allowed = po_item.quantity_ordered - po_item.quantity_received
            if qty_received > max_allowed:
                raise InvalidOperationException(
                    detail=f"Received quantity ({qty_received}) exceeds maximum allowed ({max_allowed}) for item {po_item_id}.",
                    code="INVALID_OPERATION"
                )

            # Update quantity received
            po_item.quantity_received += qty_received
            po_item.save()

            # Call adjust_inventory with INBOUND transaction type
            adjust_inventory(
                data={
                    "product_id": po_item.product.id,
                    "warehouse_id": po.warehouse.id,
                    "transaction_type": "INBOUND",
                    "quantity": qty_received,
                    "notes": f"PO Receipt for {po.po_number}"
                },
                performed_by_user_id=performed_by_user_id
            )

        # Update PO status
        all_items = po.items.all()
        fully_received = True
        any_received = False
        
        for item in all_items:
            if item.quantity_received < item.quantity_ordered:
                fully_received = False
            if item.quantity_received > 0:
                any_received = True

        if fully_received:
            po.status = PurchaseOrderStatus.RECEIVED
        elif any_received:
            po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
        else:
            po.status = PurchaseOrderStatus.APPROVED

        if actual_delivery_date:
            po.actual_delivery_date = actual_delivery_date

        po.save()

        # Dispatch Celery task
        from apps.purchase_orders.tasks import process_purchase_order_received_event
        transaction.on_commit(
            lambda: process_purchase_order_received_event.delay(po.id, performed_by_user_id)
        )

        return po

def cancel_purchase_order(po_id: int, reason: str) -> PurchaseOrder:
    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase Order not found.")

    # Only DRAFT, PENDING_APPROVAL, or APPROVED can be cancelled
    if po.status not in [PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING_APPROVAL, PurchaseOrderStatus.APPROVED]:
        raise InvalidOperationException(
            detail=f"POs with status {po.status} cannot be cancelled.",
            code="PO_CANCELLATION_NOT_ALLOWED"
        )

    po.status = PurchaseOrderStatus.CANCELLED
    if reason:
        po.notes = f"{po.notes or ''}\nCancellation Reason: {reason}".strip()
    po.save()
    return po
