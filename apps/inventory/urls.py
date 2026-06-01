from django.urls import path
from apps.inventory.views import InventoryAdjustView, InventoryTransferView, LowStockAlertView, WarehouseInventoryView

urlpatterns = [
    path('adjust/', InventoryAdjustView.as_view(), name='inventory_adjust'),
    path('transfer/', InventoryTransferView.as_view(), name='inventory_transfer'),
    path('low-stock/', LowStockAlertView.as_view(), name='inventory_low_stock'),
    path('warehouse/<int:warehouse_id>/', WarehouseInventoryView.as_view(), name='warehouse_inventory'),
]
