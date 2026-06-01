from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.purchase_orders.serializers import (
    PurchaseOrderSerializer, 
    PurchaseOrderCreateSerializer, 
    PurchaseOrderReceiveSerializer
)
from apps.purchase_orders import services as po_services
from apps.purchase_orders.models import PurchaseOrder
from core.permissions import (
    IsProcurementManagerOrAdmin, 
    IsWarehouseManagerOrAdmin, 
    IsWarehouseManagerOrAdminOrStaff
)

class PurchaseOrderListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsProcurementManagerOrAdmin()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        po = po_services.create_purchase_order(serializer.validated_data, request.user.id)
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        # List purchase orders with pagination
        queryset = PurchaseOrder.objects.all().order_by('-created_at')
        
        # Simple filters (supplier, warehouse, status)
        supplier_id = request.query_params.get('supplier_id')
        warehouse_id = request.query_params.get('warehouse_id')
        status_param = request.query_params.get('status')
        
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if status_param:
            queryset = queryset.filter(status=status_param)

        from core.pagination import StandardResultsPagination
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = PurchaseOrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = PurchaseOrderSerializer(queryset, many=True)
        return Response(serializer.data)

class PurchaseOrderSubmitView(APIView):
    permission_classes = [IsProcurementManagerOrAdmin]

    def post(self, request, pk, *args, **kwargs):
        po = po_services.submit_purchase_order(pk)
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)

class PurchaseOrderApproveView(APIView):
    permission_classes = [IsWarehouseManagerOrAdmin]

    def post(self, request, pk, *args, **kwargs):
        po = po_services.approve_purchase_order(pk, request.user.id)
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)

class PurchaseOrderReceiveView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, pk, *args, **kwargs):
        serializer = PurchaseOrderReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        po = po_services.receive_purchase_order(
            pk, 
            serializer.validated_data, 
            performed_by_user_id=request.user.id
        )
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)

class PurchaseOrderCancelView(APIView):
    permission_classes = [IsProcurementManagerOrAdmin]

    def post(self, request, pk, *args, **kwargs):
        reason = request.data.get('reason', '')
        po = po_services.cancel_purchase_order(pk, reason)
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)
