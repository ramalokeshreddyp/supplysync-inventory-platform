from django.urls import path
from apps.products.views import ProductListCreateView, ProductDetailView

urlpatterns = [
    path('', ProductListCreateView.as_view(), name='product_list_create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
]
