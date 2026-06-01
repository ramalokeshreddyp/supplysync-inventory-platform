import datetime
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from core.constants import REPORT_DASHBOARD_CACHE_TTL
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from apps.suppliers.models import Supplier
from apps.inventory.models import Inventory, InventoryTransaction
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderStatus
from apps.sales_orders.models import SalesOrder, SalesOrderStatus, SalesOrderItem

def get_dashboard_summary() -> dict:
    cache_key = 'reports:dashboard'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    total_warehouses = Warehouse.objects.filter(is_active=True).count()
    total_products = Product.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()

    # Sum of quantity_available * unit_price across all active inventory records
    val_expr = models.ExpressionWrapper(
        models.F('quantity_available') * models.F('product__unit_price'),
        output_field=models.DecimalField(max_digits=14, decimal_places=2)
    )
    total_inventory_value = Inventory.objects.filter(
        product__is_active=True,
        warehouse__is_active=True
    ).annotate(
        value=val_expr
    ).aggregate(total=models.Sum('value'))['total'] or 0.00

    # Counts
    open_purchase_orders = PurchaseOrder.objects.filter(
        status__in=[
            PurchaseOrderStatus.PENDING_APPROVAL,
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.ORDERED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED
        ]
    ).count()

    pending_sales_orders = SalesOrder.objects.filter(
        status__in=[
            SalesOrderStatus.PENDING,
            SalesOrderStatus.CONFIRMED,
            SalesOrderStatus.PROCESSING
        ]
    ).count()

    low_stock_product_count = Inventory.objects.filter(
        quantity_available__lte=models.F('product__reorder_level'),
        product__is_active=True,
        warehouse__is_active=True
    ).values('product').distinct().count()

    # Top selling products: top 5 by OUTBOUND quantity in last 30 days
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    top_selling_qs = InventoryTransaction.objects.filter(
        transaction_type='OUTBOUND',
        created_at__gte=thirty_days_ago
    ).values(
        'product_id', 
        'product__sku', 
        'product__name'
    ).annotate(
        total_dispatched=models.Sum('quantity')
    ).order_by('-total_dispatched')[:5]

    top_selling_products = []
    for item in top_selling_qs:
        top_selling_products.append({
            "product_id": item['product_id'],
            "sku": item['product__sku'],
            "product_name": item['product__name'],
            "total_dispatched": item['total_dispatched']
        })

    # Recent transactions: last 10
    recent_txs_qs = InventoryTransaction.objects.select_related(
        'product', 'warehouse', 'performed_by'
    ).order_by('-created_at')[:10]

    recent_transactions = []
    for tx in recent_txs_qs:
        recent_transactions.append({
            "id": tx.id,
            "product_id": tx.product.id,
            "sku": tx.product.sku,
            "product_name": tx.product.name,
            "warehouse_id": tx.warehouse.id,
            "warehouse_code": tx.warehouse.warehouse_code,
            "warehouse_name": tx.warehouse.name,
            "transaction_type": tx.transaction_type,
            "quantity": tx.quantity,
            "reference_id": tx.reference_id,
            "performed_by_name": tx.performed_by.full_name,
            "created_at": tx.created_at.isoformat()
        })

    result = {
        "total_warehouses": total_warehouses,
        "total_products": total_products,
        "total_suppliers": total_suppliers,
        "total_inventory_value": f"{total_inventory_value:.2f}",
        "open_purchase_orders": open_purchase_orders,
        "pending_sales_orders": pending_sales_orders,
        "low_stock_product_count": low_stock_product_count,
        "top_selling_products": top_selling_products,
        "recent_transactions": recent_transactions
    }

    cache.set(cache_key, result, timeout=REPORT_DASHBOARD_CACHE_TTL)
    return result

def get_inventory_valuation(warehouse_id: int = None) -> dict:
    warehouses_qs = Warehouse.objects.filter(is_active=True)
    if warehouse_id:
        warehouses_qs = warehouses_qs.filter(id=warehouse_id)

    warehouses_data = []
    grand_total_value = 0.0

    for wh in warehouses_qs:
        inv_qs = Inventory.objects.filter(warehouse=wh, product__is_active=True).select_related('product')
        
        products_list = []
        warehouse_total_value = 0.0

        for inv in inv_qs:
            unit_price = float(inv.product.unit_price)
            qty = inv.quantity_available
            total_value = qty * unit_price
            
            warehouse_total_value += total_value
            products_list.append({
                "sku": inv.product.sku,
                "product_name": inv.product.name,
                "quantity_available": qty,
                "unit_price": f"{unit_price:.2f}",
                "total_value": f"{total_value:.2f}"
            })

        grand_total_value += warehouse_total_value
        warehouses_data.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "warehouse_code": wh.warehouse_code,
            "products": products_list,
            "warehouse_total_value": f"{warehouse_total_value:.2f}"
        })

    return {
        "grand_total_value": f"{grand_total_value:.2f}",
        "warehouses": warehouses_data
    }

def get_purchase_order_summary(start_date, end_date, supplier_id=None, status=None) -> dict:
    po_qs = PurchaseOrder.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    if supplier_id:
        po_qs = po_qs.filter(supplier_id=supplier_id)
    if status:
        po_qs = po_qs.filter(status=status)

    total_orders = po_qs.count()
    total_value = po_qs.aggregate(total=models.Sum('total_amount'))['total'] or 0.00

    # Breakdown by status
    breakdown_qs = po_qs.values('status').annotate(
        count=models.Count('id'),
        total_value=models.Sum('total_amount')
    )
    breakdown_by_status = {}
    for item in breakdown_qs:
        breakdown_by_status[item['status']] = {
            "count": item['count'],
            "total_value": f"{item['total_value']:.2f}"
        }

    # Top suppliers: top 5 by PO value
    top_suppliers_qs = po_qs.values(
        'supplier_id', 'supplier__name'
    ).annotate(
        total_value=models.Sum('total_amount')
    ).order_by('-total_value')[:5]

    top_suppliers = []
    for item in top_suppliers_qs:
        top_suppliers.append({
            "supplier_id": item['supplier_id'],
            "supplier_name": item['supplier__name'],
            "total_value": f"{item['total_value']:.2f}"
        })

    return {
        "total_orders": total_orders,
        "total_value": f"{total_value:.2f}",
        "breakdown_by_status": breakdown_by_status,
        "top_suppliers": top_suppliers
    }

def get_sales_order_summary(start_date, end_date, warehouse_id=None, status=None) -> dict:
    so_qs = SalesOrder.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    if warehouse_id:
        so_qs = so_qs.filter(warehouse_id=warehouse_id)
    if status:
        so_qs = so_qs.filter(status=status)

    total_orders = so_qs.count()
    
    # Revenue (DELIVERED orders only)
    delivered_orders = so_qs.filter(status=SalesOrderStatus.DELIVERED)
    total_revenue = delivered_orders.aggregate(total=models.Sum('total_amount'))['total'] or 0.00
    delivered_count = delivered_orders.count()
    average_order_value = total_revenue / delivered_count if delivered_count > 0 else 0.00

    # Breakdown by status
    breakdown_qs = so_qs.values('status').annotate(
        count=models.Count('id'),
        total_value=models.Sum('total_amount')
    )
    breakdown_by_status = {}
    for item in breakdown_qs:
        breakdown_by_status[item['status']] = {
            "count": item['count'],
            "total_value": f"{item['total_value']:.2f}"
        }

    # Top products by revenue from SalesOrderItem
    top_products_qs = SalesOrderItem.objects.filter(
        sales_order__created_at__date__gte=start_date,
        sales_order__created_at__date__lte=end_date
    )
    if warehouse_id:
        top_products_qs = top_products_qs.filter(sales_order__warehouse_id=warehouse_id)
    if status:
        top_products_qs = top_products_qs.filter(sales_order__status=status)

    top_products_qs = top_products_qs.values(
        'product_id', 'product__sku', 'product__name'
    ).annotate(
        revenue=models.Sum('total_price')
    ).order_by('-revenue')[:5]

    top_products_by_revenue = []
    for item in top_products_qs:
        top_products_by_revenue.append({
            "product_id": item['product_id'],
            "sku": item['product__sku'],
            "product_name": item['product__name'],
            "revenue": f"{item['revenue']:.2f}"
        })

    return {
        "total_orders": total_orders,
        "total_revenue": f"{total_revenue:.2f}",
        "average_order_value": f"{average_order_value:.2f}",
        "breakdown_by_status": breakdown_by_status,
        "top_products_by_revenue": top_products_by_revenue
    }
