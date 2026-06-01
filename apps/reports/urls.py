from django.urls import path
from apps.reports.views import (
    DashboardReportView, 
    InventoryValuationReportView, 
    PurchaseOrderSummaryReportView, 
    SalesOrderSummaryReportView
)

urlpatterns = [
    path('dashboard/', DashboardReportView.as_view(), name='report_dashboard'),
    path('inventory-valuation/', InventoryValuationReportView.as_view(), name='report_inventory_valuation'),
    path('purchase-orders/summary/', PurchaseOrderSummaryReportView.as_view(), name='report_po_summary'),
    path('sales-orders/summary/', SalesOrderSummaryReportView.as_view(), name='report_so_summary'),
]
