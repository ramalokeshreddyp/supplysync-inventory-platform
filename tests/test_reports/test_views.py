import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
def test_dashboard_report_role_check(authenticated_staff_client):
    url = reverse('report_dashboard')
    # Staff is not allowed to view reports
    response = authenticated_staff_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_dashboard_report_success(authenticated_wm_client, sample_warehouse, sample_product, sample_supplier):
    url = reverse('report_dashboard')
    response = authenticated_wm_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "total_warehouses" in response.data
    assert "total_products" in response.data

@pytest.mark.django_db
def test_inventory_valuation_report_success(authenticated_pm_client, sample_inventory):
    url = reverse('report_inventory_valuation')
    response = authenticated_pm_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "grand_total_value" in response.data
    assert "warehouses" in response.data

@pytest.mark.django_db
def test_purchase_order_summary_report_success(authenticated_admin_client, sample_supplier):
    url = reverse('report_po_summary')
    # Requires start_date and end_date
    response = authenticated_admin_client.get(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Correct request
    response = authenticated_admin_client.get(url, {
        "start_date": "2026-06-01",
        "end_date": "2026-06-30"
    })
    assert response.status_code == status.HTTP_200_OK
    assert "total_orders" in response.data
    assert "total_value" in response.data

@pytest.mark.django_db
def test_sales_order_summary_report_success(authenticated_admin_client):
    url = reverse('report_so_summary')
    response = authenticated_admin_client.get(url, {
        "start_date": "2026-06-01",
        "end_date": "2026-06-30"
    })
    assert response.status_code == status.HTTP_200_OK
    assert "total_orders" in response.data
    assert "total_revenue" in response.data
