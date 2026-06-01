import pytest
from django.urls import reverse
from rest_framework import status
from apps.inventory.models import TransactionType

@pytest.mark.django_db
def test_adjust_inventory_endpoint_role_check(authenticated_pm_client, sample_inventory):
    url = reverse('inventory_adjust')
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.INBOUND,
        "quantity": 10
    }
    # PM client should be forbidden to adjust inventory (only WM, STAFF, ADMIN allowed)
    response = authenticated_pm_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_adjust_inventory_endpoint_success(authenticated_staff_client, sample_inventory):
    url = reverse('inventory_adjust')
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.INBOUND,
        "quantity": 50
    }
    response = authenticated_staff_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["quantity"] == 50

@pytest.mark.django_db
def test_transfer_inventory_endpoint_success(authenticated_wm_client, sample_inventory, sample_product):
    from apps.warehouses.models import Warehouse
    target_wh = Warehouse.objects.create(
        warehouse_code='WH-TRANS-VW',
        name='Target',
        location='Loc',
        city='City',
        state='ST',
        pincode='123456',
        capacity=500
    )
    
    url = reverse('inventory_transfer')
    data = {
        "product_id": sample_product.id,
        "source_warehouse_id": sample_inventory.warehouse.id,
        "destination_warehouse_id": target_wh.id,
        "quantity": 30
    }
    response = authenticated_wm_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert "reference_id" in response.data

@pytest.mark.django_db
def test_low_stock_alerts_endpoint(authenticated_staff_client, sample_inventory):
    url = reverse('inventory_low_stock')
    
    # Modify product reorder level to trigger alert
    prod = sample_inventory.product
    prod.reorder_level = 150 # available is 100
    prod.save()
    
    response = authenticated_staff_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) > 0
    assert response.data[0]["sku"] == prod.sku
    assert response.data[0]["deficit"] == 50

@pytest.mark.django_db
def test_warehouse_inventory_snapshot(authenticated_staff_client, sample_warehouse):
    url = reverse('warehouse_inventory', kwargs={"warehouse_id": sample_warehouse.id})
    response = authenticated_staff_client.get(url)
    assert response.status_code == status.HTTP_200_OK
