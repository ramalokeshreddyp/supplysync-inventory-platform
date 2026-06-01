import pytest
from unittest.mock import patch
from apps.inventory import services as inventory_services
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from core.exceptions import InsufficientInventoryException

@pytest.mark.django_db(transaction=True)
@patch('apps.inventory.tasks.process_inventory_updated_event.delay')
def test_adjust_inventory_success(mock_celery, sample_inventory, staff_user):
    # Adjust stock (Inbound)
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.INBOUND,
        "quantity": 50,
        "notes": "Test Inbound adjustment"
    }
    
    tx = inventory_services.adjust_inventory(data, performed_by_user_id=staff_user.id)
    
    assert tx.id is not None
    assert tx.transaction_type == TransactionType.INBOUND
    assert tx.quantity == 50
    
    # Reload inventory
    inv = Inventory.objects.get(id=sample_inventory.id)
    assert inv.quantity_available == 150 # 100 + 50
    mock_celery.assert_called_once_with(sample_inventory.product.id, sample_inventory.warehouse.id, TransactionType.INBOUND, 50)

@pytest.mark.django_db
def test_adjust_inventory_insufficient_stock(sample_inventory, staff_user):
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.OUTBOUND,
        "quantity": 200, # sample has 100
        "notes": "Should fail"
    }
    
    with pytest.raises(InsufficientInventoryException):
        inventory_services.adjust_inventory(data, performed_by_user_id=staff_user.id)

@pytest.mark.django_db
@patch('apps.inventory.tasks.process_inventory_updated_event.delay')
def test_adjust_inventory_damage_report(mock_celery, sample_inventory, staff_user):
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.DAMAGE_REPORT,
        "quantity": 30,
        "notes": "Damaged items"
    }
    
    tx = inventory_services.adjust_inventory(data, performed_by_user_id=staff_user.id)
    
    inv = Inventory.objects.get(id=sample_inventory.id)
    assert inv.quantity_available == 70 # 100 - 30
    assert inv.quantity_damaged == 30 # 0 + 30

@pytest.mark.django_db(transaction=True)
@patch('apps.inventory.tasks.process_inventory_transfer_event.delay')
def test_transfer_inventory_success(mock_celery, sample_inventory, staff_user, sample_product):
    # Create target warehouse
    from apps.warehouses.models import Warehouse
    target_wh = Warehouse.objects.create(
        warehouse_code='WH-DEST01',
        name='Target Wh',
        location='Elsewhere',
        city='Dest City',
        state='TS',
        pincode='000000',
        capacity=500
    )
    
    data = {
        "product_id": sample_product.id,
        "source_warehouse_id": sample_inventory.warehouse.id,
        "destination_warehouse_id": target_wh.id,
        "quantity": 40,
        "notes": "Inventory transfer"
    }
    
    res = inventory_services.transfer_inventory(data, performed_by_user_id=staff_user.id)
    
    assert "reference_id" in res
    assert res["quantity_transferred"] == 40
    
    # Check quantities
    source_inv = Inventory.objects.get(product=sample_product, warehouse=sample_inventory.warehouse)
    dest_inv = Inventory.objects.get(product=sample_product, warehouse=target_wh)
    
    assert source_inv.quantity_available == 60 # 100 - 40
    assert dest_inv.quantity_available == 40 # 0 + 40
    
    mock_celery.assert_called_once_with(sample_product.id, sample_inventory.warehouse.id, target_wh.id, 40)

@pytest.mark.django_db
def test_transfer_inventory_insufficient_stock(sample_inventory, staff_user, sample_product):
    from apps.warehouses.models import Warehouse
    target_wh = Warehouse.objects.create(
        warehouse_code='WH-DEST02',
        name='Target Wh 2',
        location='Elsewhere',
        city='Dest City',
        state='TS',
        pincode='000000',
        capacity=500
    )
    
    data = {
        "product_id": sample_product.id,
        "source_warehouse_id": sample_inventory.warehouse.id,
        "destination_warehouse_id": target_wh.id,
        "quantity": 150, # exceeds 100
        "notes": "Should fail"
    }
    
    with pytest.raises(InsufficientInventoryException):
        inventory_services.transfer_inventory(data, performed_by_user_id=staff_user.id)
