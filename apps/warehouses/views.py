from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache

from apps.warehouses.serializers import WarehouseSerializer
from apps.warehouses import services as warehouse_services
from apps.warehouses.models import Warehouse
from core.permissions import IsAdminUser, IsWarehouseManagerOrAdmin
from rest_framework.permissions import IsAuthenticated

class WarehouseListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = WarehouseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = warehouse_services.create_warehouse(serializer.validated_data)
        return Response(WarehouseSerializer(warehouse).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        # We can implement list caching
        cache_key = 'warehouses:list'
        
        # Note: listing supports query parameters city, state. If present, don't use cache
        city = request.query_params.get('city')
        state = request.query_params.get('state')
        
        if not city and not state:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                # Apply pagination manually if cached
                page = self.paginate_queryset(cached_data)
                if page is not None:
                    return self.get_paginated_response(page)
                return Response(cached_data)

        queryset = Warehouse.objects.all()
        if city:
            queryset = queryset.filter(city__iexact=city)
        if state:
            queryset = queryset.filter(state__iexact=state)

        # Order for consistency
        queryset = queryset.order_by('id')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WarehouseSerializer(page, many=True)
            if not city and not state:
                cache.set(cache_key, serializer.data, timeout=900) # 15 min WAREHOUSE_LIST_CACHE_TTL
            return self.get_paginated_response(serializer.data)

        serializer = WarehouseSerializer(queryset, many=True)
        if not city and not state:
            cache.set(cache_key, serializer.data, timeout=900)
        return Response(serializer.data)

    def paginate_queryset(self, queryset):
        paginator = self.request.query_params.get('page')
        if paginator or hasattr(self, 'paginator'):
            if not hasattr(self, '_paginator'):
                from core.pagination import StandardResultsPagination
                self._paginator = StandardResultsPagination()
            # If queryset is list
            if isinstance(queryset, list):
                # Turn list of dict into dummy list of objects or paginated slice
                return self._paginator.paginate_queryset(queryset, self.request, view=self)
            return self._paginator.paginate_queryset(queryset, self.request, view=self)
        return None

    def get_paginated_response(self, data):
        return self._paginator.get_paginated_response(data)

class WarehouseDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['PUT', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get(self, request, pk, *args, **kwargs):
        summary_data = warehouse_services.get_warehouse_with_summary(pk)
        return Response(summary_data, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        serializer = WarehouseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        warehouse = warehouse_services.update_warehouse(pk, serializer.validated_data)
        return Response(WarehouseSerializer(warehouse).data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        warehouse_services.delete_warehouse(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
