import pytest
from unittest.mock import patch
from apps.sales_orders import services as so_services
from apps.sales_orders.models import SalesOrder, SalesOrderItem, SalesOrderStatus
from apps.inventory.models import Inventory
from core.exceptions import InsufficientInventoryException

@pytest.mark.django_db(transaction=True)
@patch('apps.sales_orders.tasks.process_sales_order_created_event.delay')
def test_create_sales_order_success(mock_celery, sample_inventory, staff_user):
    data = {
        "customer_name": "Acme Corp",
        "customer_email": "acme@test.com",
        "customer_phone": "1234567890",
        "shipping_address": "Acme Road 1",
        "warehouse_id": sample_inventory.warehouse.id,
        "items": [
            {
                "product_id": sample_inventory.product.id,
                "quantity": 30
            }
        ]
    }
    # sample_inventory has 100 available, 10 reserved
    so = so_services.create_sales_order(data, created_by_user_id=staff_user.id)
    
    assert so.id is not None
    assert so.status == SalesOrderStatus.CONFIRMED
    assert so.total_amount == 30 * sample_inventory.product.unit_price
    
    # Reload inventory
    inv = Inventory.objects.get(id=sample_inventory.id)
    assert inv.quantity_available == 70 # 100 - 30
    assert inv.quantity_reserved == 40 # 10 + 30
    
    mock_celery.assert_called_once_with(so.id, staff_user.id)

@pytest.mark.django_db
def test_create_sales_order_insufficient_stock(sample_inventory, staff_user):
    data = {
        "customer_name": "Acme Corp",
        "customer_email": "acme@test.com",
        "customer_phone": "1234567890",
        "shipping_address": "Acme Road 1",
        "warehouse_id": sample_inventory.warehouse.id,
        "items": [
            {
                "product_id": sample_inventory.product.id,
                "quantity": 150 # exceeds 100
            }
        ]
    }
    
    with pytest.raises(InsufficientInventoryException) as excinfo:
        so_services.create_sales_order(data, created_by_user_id=staff_user.id)
        
    assert excinfo.value.detail["short_items"][0]["sku"] == sample_inventory.product.sku
    assert int(excinfo.value.detail["short_items"][0]["available_quantity"]) == 100

@pytest.mark.django_db
def test_dispatch_sales_order_success(sample_inventory, staff_user):
    data = {
        "customer_name": "Acme Corp",
        "customer_email": "acme@test.com",
        "customer_phone": "1234567890",
        "shipping_address": "Acme Road 1",
        "warehouse_id": sample_inventory.warehouse.id,
        "items": [{"product_id": sample_inventory.product.id, "quantity": 40}]
    }
    so = so_services.create_sales_order(data, created_by_user_id=staff_user.id)
    
    # Dispatch
    so = so_services.dispatch_sales_order(so.id)
    assert so.status == SalesOrderStatus.DISPATCHED
    assert so.dispatched_at is not None
    
    # Check inventory
    inv = Inventory.objects.get(id=sample_inventory.id)
    assert inv.quantity_available == 60 # 100 - 40
    assert inv.quantity_reserved == 10 # original reserved remains, order reserved is released
