from django.urls import path
from apps.warehouses.views import WarehouseListCreateView, WarehouseDetailView

urlpatterns = [
    path('', WarehouseListCreateView.as_view(), name='warehouse_list_create'),
    path('<int:pk>/', WarehouseDetailView.as_view(), name='warehouse_detail'),
]
