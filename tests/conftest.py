import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.warehouses.models import Warehouse
from apps.categories.models import Category
from apps.products.models import Product
from apps.suppliers.models import Supplier
from apps.inventory.models import Inventory

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email='admin@supplysync.com',
        username='admin',
        full_name='System Admin',
        password='Password@123',
        role=UserRole.ADMIN,
        is_staff=True
    )

@pytest.fixture
def warehouse_manager_user(db):
    return User.objects.create_user(
        email='wm@supplysync.com',
        username='wm_manager',
        full_name='Warehouse Manager',
        password='Password@123',
        role=UserRole.WAREHOUSE_MANAGER
    )

@pytest.fixture
def procurement_manager_user(db):
    return User.objects.create_user(
        email='pm@supplysync.com',
        username='pm_manager',
        full_name='Procurement Manager',
        password='Password@123',
        role=UserRole.PROCUREMENT_MANAGER
    )

@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email='staff@supplysync.com',
        username='staff_user',
        full_name='Warehouse Staff',
        password='Password@123',
        role=UserRole.STAFF
    )

@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.fixture
def authenticated_wm_client(api_client, warehouse_manager_user):
    api_client.force_authenticate(user=warehouse_manager_user)
    return api_client

@pytest.fixture
def authenticated_pm_client(api_client, procurement_manager_user):
    api_client.force_authenticate(user=procurement_manager_user)
    return api_client

@pytest.fixture
def authenticated_staff_client(api_client, staff_user):
    api_client.force_authenticate(user=staff_user)
    return api_client

@pytest.fixture
def sample_warehouse(db):
    return Warehouse.objects.create(
        warehouse_code='WH-TEST01',
        name='Test Warehouse 1',
        location='123 Test St',
        city='Test City',
        state='TS',
        pincode='123456',
        capacity=1000,
        is_active=True
    )

@pytest.fixture
def sample_category(db):
    return Category.objects.create(
        category_code='CAT-TEST',
        name='Test Category',
        description='Category for testing'
    )

@pytest.fixture
def sample_product(db, sample_category):
    return Product.objects.create(
        sku='SKU-CAT-TEST-8CHARSEC',
        name='Test Product 1',
        description='Product for testing',
        category=sample_category,
        unit_price=10.50,
        unit_of_measure='pieces',
        reorder_level=10,
        is_active=True
    )

@pytest.fixture
def sample_supplier(db):
    return Supplier.objects.create(
        supplier_code='SUP-TEST01',
        name='Test Supplier 1',
        contact_person='John Doe',
        email='supplier@test.com',
        phone='9876543210',
        address='456 Supplier Rd',
        city='Supplier City',
        state='SS',
        pincode='654321',
        gstin='22AAAAA0000A1Z5',
        is_active=True
    )

@pytest.fixture
def sample_inventory(db, sample_product, sample_warehouse):
    return Inventory.objects.create(
        product=sample_product,
        warehouse=sample_warehouse,
        quantity_available=100,
        quantity_reserved=10,
        quantity_damaged=0
    )
