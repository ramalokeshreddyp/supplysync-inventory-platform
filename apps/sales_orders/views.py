from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.sales_orders.serializers import SalesOrderSerializer, SalesOrderCreateSerializer
from apps.sales_orders import services as so_services
from apps.sales_orders.models import SalesOrder
from core.permissions import IsWarehouseManagerOrAdminOrStaff

class SalesOrderListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsWarehouseManagerOrAdminOrStaff()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = SalesOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        so = so_services.create_sales_order(serializer.validated_data, request.user.id)
        return Response(SalesOrderSerializer(so).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = SalesOrder.objects.all().order_by('-created_at')
        
        # Filters (warehouse, status)
        warehouse_id = request.query_params.get('warehouse_id')
        status_param = request.query_params.get('status')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if status_param:
            queryset = queryset.filter(status=status_param)

        from core.pagination import StandardResultsPagination
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = SalesOrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = SalesOrderSerializer(queryset, many=True)
        return Response(serializer.data)

class SalesOrderDispatchView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, pk, *args, **kwargs):
        so = so_services.dispatch_sales_order(pk)
        return Response(SalesOrderSerializer(so).data, status=status.HTTP_200_OK)

class SalesOrderDeliverView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, pk, *args, **kwargs):
        so = so_services.deliver_sales_order(pk)
        return Response(SalesOrderSerializer(so).data, status=status.HTTP_200_OK)

class SalesOrderCancelView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, pk, *args, **kwargs):
        reason = request.data.get('reason', '')
        so = so_services.cancel_sales_order(pk, reason)
        return Response(SalesOrderSerializer(so).data, status=status.HTTP_200_OK)
