import pytest
from unittest.mock import patch
from rest_framework.exceptions import PermissionDenied
from apps.purchase_orders import services as po_services
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from core.exceptions import InvalidOperationException

@pytest.mark.django_db
def test_create_purchase_order_success(sample_supplier, sample_warehouse, sample_product, procurement_manager_user):
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "expected_delivery_date": "2026-07-01",
        "items": [
            {
                "product_id": sample_product.id,
                "quantity_ordered": 100,
                "unit_price": 10.00
            }
        ]
    }
    po = po_services.create_purchase_order(data, created_by_user_id=procurement_manager_user.id)
    
    assert po.id is not None
    assert po.po_number.startswith("PO-")
    assert po.status == PurchaseOrderStatus.DRAFT
    assert po.total_amount == 1000.00
    assert po.items.count() == 1

@pytest.mark.django_db
def test_submit_purchase_order_success(sample_supplier, sample_warehouse, sample_product, procurement_manager_user):
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "items": [{"product_id": sample_product.id, "quantity_ordered": 10, "unit_price": 5.00}]
    }
    po = po_services.create_purchase_order(data, created_by_user_id=procurement_manager_user.id)
    po = po_services.submit_purchase_order(po.id)
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

@pytest.mark.django_db
def test_submit_purchase_order_no_items(sample_supplier, sample_warehouse, procurement_manager_user):
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "items": []
    }
    po = po_services.create_purchase_order(data, created_by_user_id=procurement_manager_user.id)
    
    with pytest.raises(InvalidOperationException):
        po_services.submit_purchase_order(po.id)

@pytest.mark.django_db
def test_approve_purchase_order_success(sample_supplier, sample_warehouse, sample_product, procurement_manager_user, warehouse_manager_user):
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "items": [{"product_id": sample_product.id, "quantity_ordered": 10, "unit_price": 5.00}]
    }
    po = po_services.create_purchase_order(data, created_by_user_id=procurement_manager_user.id)
    po = po_services.submit_purchase_order(po.id)
    
    # Approve by WM
    po = po_services.approve_purchase_order(po.id, approved_by_user_id=warehouse_manager_user.id)
    assert po.status == PurchaseOrderStatus.APPROVED
    assert po.approved_by == warehouse_manager_user

@pytest.mark.django_db
def test_approve_purchase_order_self_approval(sample_supplier, sample_warehouse, sample_product, warehouse_manager_user):
    # WM creates the PO
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "items": [{"product_id": sample_product.id, "quantity_ordered": 10, "unit_price": 5.00}]
    }
    po = po_services.create_purchase_order(data, created_by_user_id=warehouse_manager_user.id)
    po = po_services.submit_purchase_order(po.id)
    
    # WM attempts to self-approve
    with pytest.raises(PermissionDenied):
        po_services.approve_purchase_order(po.id, approved_by_user_id=warehouse_manager_user.id)

@pytest.mark.django_db(transaction=True)
@patch('apps.purchase_orders.tasks.process_purchase_order_received_event.delay')
def test_receive_purchase_order_success(mock_celery, sample_supplier, sample_warehouse, sample_product, procurement_manager_user, warehouse_manager_user, staff_user):
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "items": [{"product_id": sample_product.id, "quantity_ordered": 100, "unit_price": 10.00}]
    }
    po = po_services.create_purchase_order(data, created_by_user_id=procurement_manager_user.id)
    po = po_services.submit_purchase_order(po.id)
    po = po_services.approve_purchase_order(po.id, approved_by_user_id=warehouse_manager_user.id)
    
    # Mocking status transition from APPROVED to RECEIVED
    # Let's say order is placed (or we directly receive it)
    receive_data = {
        "items": [
            {
                "po_item_id": po.items.first().id,
                "quantity_received": 100
            }
        ],
        "actual_delivery_date": "2026-06-01"
    }
    
    po = po_services.receive_purchase_order(po.id, receive_data, performed_by_user_id=staff_user.id)
    
    assert po.status == PurchaseOrderStatus.RECEIVED
    assert po.items.first().quantity_received == 100
    mock_celery.assert_called_once_with(po.id, staff_user.id)

@pytest.mark.django_db
def test_cancel_purchase_order_success(sample_supplier, sample_warehouse, sample_product, procurement_manager_user):
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "items": [{"product_id": sample_product.id, "quantity_ordered": 10, "unit_price": 5.00}]
    }
    po = po_services.create_purchase_order(data, created_by_user_id=procurement_manager_user.id)
    po = po_services.cancel_purchase_order(po.id, reason="No longer needed")
    assert po.status == PurchaseOrderStatus.CANCELLED
