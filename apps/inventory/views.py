from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.inventory.serializers import (
    InventorySerializer, 
    InventoryTransactionSerializer,
    InventoryAdjustSerializer, 
    InventoryTransferSerializer
)
from apps.inventory import services as inventory_services
from apps.inventory.models import Inventory
from core.permissions import IsWarehouseManagerOrAdminOrStaff

class InventoryAdjustView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, *args, **kwargs):
        serializer = InventoryAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tx = inventory_services.adjust_inventory(
            serializer.validated_data, 
            performed_by_user_id=request.user.id
        )
        return Response(InventoryTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

class InventoryTransferView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, *args, **kwargs):
        serializer = InventoryTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        res = inventory_services.transfer_inventory(
            serializer.validated_data,
            performed_by_user_id=request.user.id
        )
        return Response(res, status=status.HTTP_200_OK)

class LowStockAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        alerts = inventory_services.get_low_stock_alerts()
        return Response(alerts, status=status.HTTP_200_OK)

class WarehouseInventoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, warehouse_id, *args, **kwargs):
        queryset = Inventory.objects.filter(warehouse_id=warehouse_id).select_related('product', 'warehouse').order_by('id')
        
        from core.pagination import StandardResultsPagination
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = InventorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = InventorySerializer(queryset, many=True)
        return Response(serializer.data)
