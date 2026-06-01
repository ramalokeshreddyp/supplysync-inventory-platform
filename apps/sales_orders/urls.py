from django.urls import path
from apps.sales_orders.views import (
    SalesOrderListCreateView, 
    SalesOrderDispatchView, 
    SalesOrderDeliverView, 
    SalesOrderCancelView
)

urlpatterns = [
    path('', SalesOrderListCreateView.as_view(), name='so_list_create'),
    path('<int:pk>/dispatch/', SalesOrderDispatchView.as_view(), name='so_dispatch'),
    path('<int:pk>/deliver/', SalesOrderDeliverView.as_view(), name='so_deliver'),
    path('<int:pk>/cancel/', SalesOrderCancelView.as_view(), name='so_cancel'),
]
