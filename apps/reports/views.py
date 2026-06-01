import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.reports import services as report_services
from core.permissions import IsWarehouseManagerOrAdminOrProcurementManager

class DashboardReportView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrProcurementManager]

    def get(self, request, *args, **kwargs):
        data = report_services.get_dashboard_summary()
        return Response(data, status=status.HTTP_200_OK)

class InventoryValuationReportView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrProcurementManager]

    def get(self, request, *args, **kwargs):
        wh_id = request.query_params.get('warehouse_id')
        if wh_id:
            try:
                wh_id = int(wh_id)
            except ValueError:
                raise ValidationError("warehouse_id must be an integer.")
                
        data = report_services.get_inventory_valuation(warehouse_id=wh_id)
        return Response(data, status=status.HTTP_200_OK)

class PurchaseOrderSummaryReportView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrProcurementManager]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        supplier_id = request.query_params.get('supplier_id')
        status_param = request.query_params.get('status')

        if not start_date_str or not end_date_str:
            raise ValidationError("Both start_date and end_date parameters are required.")

        try:
            start_date = datetime.date.fromisoformat(start_date_str)
            end_date = datetime.date.fromisoformat(end_date_str)
        except ValueError:
            raise ValidationError("Dates must be in YYYY-MM-DD format.")

        if supplier_id:
            try:
                supplier_id = int(supplier_id)
            except ValueError:
                raise ValidationError("supplier_id must be an integer.")

        data = report_services.get_purchase_order_summary(
            start_date=start_date,
            end_date=end_date,
            supplier_id=supplier_id,
            status=status_param
        )
        return Response(data, status=status.HTTP_200_OK)

class SalesOrderSummaryReportView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrProcurementManager]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        warehouse_id = request.query_params.get('warehouse_id')
        status_param = request.query_params.get('status')

        if not start_date_str or not end_date_str:
            raise ValidationError("Both start_date and end_date parameters are required.")

        try:
            start_date = datetime.date.fromisoformat(start_date_str)
            end_date = datetime.date.fromisoformat(end_date_str)
        except ValueError:
            raise ValidationError("Dates must be in YYYY-MM-DD format.")

        if warehouse_id:
            try:
                warehouse_id = int(warehouse_id)
            except ValueError:
                raise ValidationError("warehouse_id must be an integer.")

        data = report_services.get_sales_order_summary(
            start_date=start_date,
            end_date=end_date,
            warehouse_id=warehouse_id,
            status=status_param
        )
        return Response(data, status=status.HTTP_200_OK)
