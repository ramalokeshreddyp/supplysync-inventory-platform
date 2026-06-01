from django.urls import path
from apps.suppliers.views import SupplierListCreateView, SupplierDetailView

urlpatterns = [
    path('', SupplierListCreateView.as_view(), name='supplier_list_create'),
    path('<int:pk>/', SupplierDetailView.as_view(), name='supplier_detail'),
]
