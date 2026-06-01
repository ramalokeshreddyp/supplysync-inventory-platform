from django.core.management.base import BaseCommand
from django.test import Client
import json


class Command(BaseCommand):
    help = 'Run E2E smoke tests: register, create category/warehouse/product, adjust inventory.'

    def handle(self, *args, **options):
        c = Client()

        self.stdout.write('Registering admin user...')
        reg = c.post('/api/v1/auth/register/', {
            'username': 'e2e_admin',
            'email': 'e2e_admin@example.com',
            'full_name': 'E2E Admin',
            'password': 'StrongPassw0rd!',
            'role': 'ADMIN'
        }, content_type='application/json')
        self.stdout.write(f'Register status: {reg.status_code}')
        try:
            self.stdout.write(json.dumps(reg.json(), indent=2))
        except Exception:
            self.stdout.write(str(reg.content))
        if reg.status_code != 201:
            # if user exists, attempt login
            try:
                err = reg.json()
                errs = err.get('errors') or err
            except Exception:
                errs = None
            if reg.status_code == 400 and errs:
                self.stdout.write('User exists, attempting login...')
                login_resp = c.post('/api/v1/auth/login/', json.dumps({'email': 'e2e_admin@example.com', 'password': 'StrongPassw0rd!'}), content_type='application/json')
                self.stdout.write(f'Login status: {login_resp.status_code}')
                try:
                    self.stdout.write(json.dumps(login_resp.json(), indent=2))
                except Exception:
                    self.stdout.write(str(login_resp.content))
                if login_resp.status_code != 200:
                    raise SystemExit(2)
                token = login_resp.json().get('access_token')
            else:
                raise SystemExit(2)

        token = reg.json().get('access_token') if reg.status_code == 201 else token
        if not token:
            self.stdout.write('No access token returned')
            raise SystemExit(3)

        auth_header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

        self.stdout.write('Creating category...')
        cat = c.post('/api/v1/categories/', json.dumps({'name': 'Electronics'}), content_type='application/json', **auth_header)
        self.stdout.write(f'Category status: {cat.status_code}')
        try:
            self.stdout.write(json.dumps(cat.json(), indent=2))
        except Exception:
            self.stdout.write(str(cat.content))
        if cat.status_code != 201:
            raise SystemExit(4)

        category_id = cat.json()['id']

        self.stdout.write('Creating warehouse...')
        wh_payload = {
            'warehouse_code': 'WH-E2E-1',
            'name': 'E2E Warehouse',
            'location': '123 Test Blvd',
            'city': 'Testville',
            'state': 'TS',
            'pincode': '12345',
            'capacity': 1000
        }
        wh = c.post('/api/v1/warehouses/', json.dumps(wh_payload), content_type='application/json', **auth_header)
        self.stdout.write(f'Warehouse status: {wh.status_code}')
        if wh.status_code == 409:
            self.stdout.write('Warehouse code conflict, retrying without explicit code...')
            wh_payload.pop('warehouse_code')
            wh = c.post('/api/v1/warehouses/', json.dumps(wh_payload), content_type='application/json', **auth_header)

        try:
            self.stdout.write(json.dumps(wh.json(), indent=2))
        except Exception:
            self.stdout.write(str(wh.content))
        if wh.status_code != 201:
            raise SystemExit(5)

        warehouse_id = wh.json()['id']

        self.stdout.write('Creating product...')
        prod_payload = {
            'sku': 'E2E-SKU-001',
            'name': 'E2E Widget',
            'description': 'Test product',
            'category_id': category_id,
            'unit_price': '9.99',
            'unit_of_measure': 'pcs',
            'reorder_level': 10
        }
        prod = c.post('/api/v1/products/', json.dumps(prod_payload), content_type='application/json', **auth_header)
        self.stdout.write(f'Product status: {prod.status_code}')
        if prod.status_code == 409:
            self.stdout.write('Product SKU conflict, retrying without explicit sku...')
            prod_payload.pop('sku')
            prod = c.post('/api/v1/products/', json.dumps(prod_payload), content_type='application/json', **auth_header)
        try:
            self.stdout.write(json.dumps(prod.json(), indent=2))
        except Exception:
            self.stdout.write(str(prod.content))
        if prod.status_code != 201:
            raise SystemExit(6)

        product_id = prod.json()['id']

        self.stdout.write('Adjusting inventory (INBOUND +100)...')
        adj_payload = {
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'transaction_type': 'INBOUND',
            'quantity': 100,
            'notes': 'Initial stock'
        }
        adj = c.post('/api/v1/inventory/adjust/', json.dumps(adj_payload), content_type='application/json', **auth_header)
        self.stdout.write(f'Adjust status: {adj.status_code}')
        try:
            self.stdout.write(json.dumps(adj.json(), indent=2))
        except Exception:
            self.stdout.write(str(adj.content))
        if adj.status_code != 201:
            raise SystemExit(7)

        self.stdout.write('Fetching warehouse inventory...')
        inv = c.get(f'/api/v1/inventory/warehouse/{warehouse_id}/', **auth_header)
        self.stdout.write(f'Inventory status: {inv.status_code}')
        try:
            self.stdout.write(json.dumps(inv.json(), indent=2))
        except Exception:
            self.stdout.write(str(inv.content))
        if inv.status_code != 200:
            raise SystemExit(8)

        # ---- Purchase Order flow ----
        self.stdout.write('Creating supplier...')
        supplier_payload = {
            'name': 'E2E Supplier',
            'contact_person': 'Supplier Rep',
            'email': 'supplier@example.com',
            'phone': '9999999999',
            'address': '1 Supplier St',
            'city': 'SupplyCity',
            'state': 'SS',
            'pincode': '54321'
        }
        sup = c.post('/api/v1/suppliers/', json.dumps(supplier_payload), content_type='application/json', **auth_header)
        self.stdout.write(f'Supplier status: {sup.status_code}')
        try:
            self.stdout.write(json.dumps(sup.json(), indent=2))
        except Exception:
            self.stdout.write(str(sup.content))
        if sup.status_code != 201:
            raise SystemExit(9)

        supplier_id = sup.json()['id']

        self.stdout.write('Creating purchase order (DRAFT)...')
        po_payload = {
            'supplier_id': supplier_id,
            'warehouse_id': warehouse_id,
            'items': [
                {'product_id': product_id, 'quantity_ordered': 50, 'unit_price': '5.00'}
            ]
        }
        po = c.post('/api/v1/purchase-orders/', json.dumps(po_payload), content_type='application/json', **auth_header)
        self.stdout.write(f'PO create status: {po.status_code}')
        try:
            self.stdout.write(json.dumps(po.json(), indent=2))
        except Exception:
            self.stdout.write(str(po.content))
        if po.status_code != 201:
            raise SystemExit(10)

        po_id = po.json()['id']

        self.stdout.write('Submitting PO...')
        sub = c.post(f'/api/v1/purchase-orders/{po_id}/submit/', content_type='application/json', **auth_header)
        self.stdout.write(f'PO submit status: {sub.status_code}')
        if sub.status_code != 200:
            raise SystemExit(11)

        # Ensure there's a warehouse manager to approve/receive the PO
        self.stdout.write('Creating warehouse manager user...')
        mgr_reg = c.post('/api/v1/auth/register/', {
            'username': 'e2e_wh_mgr',
            'email': 'e2e_wh_mgr@example.com',
            'full_name': 'E2E WarehouseMgr',
            'password': 'StrongPassw0rd!',
            'role': 'WAREHOUSE_MANAGER'
        }, content_type='application/json')
        self.stdout.write(f'WM register status: {mgr_reg.status_code}')
        try:
            self.stdout.write(json.dumps(mgr_reg.json(), indent=2))
        except Exception:
            self.stdout.write(str(mgr_reg.content))

        if mgr_reg.status_code != 201:
            # If already exists, login
            if mgr_reg.status_code == 400:
                self.stdout.write('Warehouse manager exists, attempting login...')
                mgr_login = c.post('/api/v1/auth/login/', json.dumps({'email': 'e2e_wh_mgr@example.com', 'password': 'StrongPassw0rd!'}), content_type='application/json')
                self.stdout.write(f'WM login status: {mgr_login.status_code}')
                try:
                    self.stdout.write(json.dumps(mgr_login.json(), indent=2))
                except Exception:
                    self.stdout.write(str(mgr_login.content))
                if mgr_login.status_code != 200:
                    raise SystemExit(20)
                mgr_token = mgr_login.json().get('access_token')
            else:
                raise SystemExit(20)
        else:
            mgr_token = mgr_reg.json().get('access_token')

        auth_header_mgr = {'HTTP_AUTHORIZATION': f'Bearer {mgr_token}'}

        self.stdout.write('Approving PO...')
        appv = c.post(f'/api/v1/purchase-orders/{po_id}/approve/', content_type='application/json', **auth_header_mgr)
        self.stdout.write(f'PO approve status: {appv.status_code}')
        if appv.status_code != 200:
            raise SystemExit(12)

        # Receive the PO fully
        po_data = po.json()
        items = po_data.get('items') or appv.json().get('items')
        if not items:
            raise SystemExit(13)

        self.stdout.write('Receiving PO (full)...')
        receive_items = [{'po_item_id': items[0]['id'], 'quantity_received': items[0]['quantity_ordered']}]
        recv_payload = {'items': receive_items}
        recv = c.post(f'/api/v1/purchase-orders/{po_id}/receive/', json.dumps(recv_payload), content_type='application/json', **auth_header_mgr)
        self.stdout.write(f'PO receive status: {recv.status_code}')
        try:
            self.stdout.write(json.dumps(recv.json(), indent=2))
        except Exception:
            self.stdout.write(str(recv.content))
        if recv.status_code != 200:
            raise SystemExit(14)

        # ---- Sales Order flow ----
        self.stdout.write('Creating sales order (reserve inventory)...')
        so_payload = {
            'customer_name': 'ACME Corp',
            'customer_email': 'orders@acme.test',
            'customer_phone': '8888888888',
            'shipping_address': '100 Client Rd',
            'warehouse_id': warehouse_id,
            'items': [{'product_id': product_id, 'quantity': 10}]
        }
        so = c.post('/api/v1/sales-orders/', json.dumps(so_payload), content_type='application/json', **auth_header)
        self.stdout.write(f'SO create status: {so.status_code}')
        try:
            self.stdout.write(json.dumps(so.json(), indent=2))
        except Exception:
            self.stdout.write(str(so.content))
        if so.status_code != 201:
            raise SystemExit(15)

        so_id = so.json()['id']

        self.stdout.write('Dispatching sales order...')
        dsp = c.post(f'/api/v1/sales-orders/{so_id}/dispatch/', content_type='application/json', **auth_header)
        self.stdout.write(f'SO dispatch status: {dsp.status_code}')
        if dsp.status_code != 200:
            raise SystemExit(16)

        self.stdout.write('Delivering sales order...')
        dlv = c.post(f'/api/v1/sales-orders/{so_id}/deliver/', content_type='application/json', **auth_header)
        self.stdout.write(f'SO deliver status: {dlv.status_code}')
        if dlv.status_code != 200:
            raise SystemExit(17)

        self.stdout.write('E2E smoke succeeded')