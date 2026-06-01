from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.suppliers.serializers import SupplierSerializer
from apps.suppliers import services as supplier_services
from core.permissions import IsProcurementManagerOrAdmin

class SupplierListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsProcurementManagerOrAdmin()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = SupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = supplier_services.create_supplier(serializer.validated_data)
        return Response(SupplierSerializer(supplier).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Build filters dictionary from query parameters
        filters = {}
        for param in ['city', 'state', 'name', 'is_active']:
            val = request.query_params.get(param)
            if val is not None:
                if param == 'is_active':
                    filters['is_active'] = val.lower() == 'true'
                elif param == 'name':
                    filters['name__icontains'] = val
                else:
                    filters[param] = val

        queryset = supplier_services.list_suppliers(filters, page, page_size)
        serializer = SupplierSerializer(queryset, many=True)
        return Response({
            "results": serializer.data,
            "page": page,
            "page_size": page_size
        })

class SupplierDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['PUT', 'DELETE']:
            return [IsProcurementManagerOrAdmin()]
        return [IsAuthenticated()]

    def get(self, request, pk, *args, **kwargs):
        supplier = supplier_services.get_supplier_by_id(pk)
        return Response(SupplierSerializer(supplier).data, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        serializer = SupplierSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        supplier = supplier_services.update_supplier(pk, serializer.validated_data)
        return Response(SupplierSerializer(supplier).data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        supplier_services.delete_supplier(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
