from django.urls import path
from apps.purchase_orders.views import (
    PurchaseOrderListCreateView, 
    PurchaseOrderSubmitView, 
    PurchaseOrderApproveView, 
    PurchaseOrderReceiveView, 
    PurchaseOrderCancelView
)

urlpatterns = [
    path('', PurchaseOrderListCreateView.as_view(), name='po_list_create'),
    path('<int:pk>/submit/', PurchaseOrderSubmitView.as_view(), name='po_submit'),
    path('<int:pk>/approve/', PurchaseOrderApproveView.as_view(), name='po_approve'),
    path('<int:pk>/receive/', PurchaseOrderReceiveView.as_view(), name='po_receive'),
    path('<int:pk>/cancel/', PurchaseOrderCancelView.as_view(), name='po_cancel'),
]
