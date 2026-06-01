from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache

from apps.products.serializers import ProductSerializer
from apps.products import services as product_services
from apps.products.models import Product
from apps.products.filters import ProductFilter
from core.permissions import IsWarehouseManagerOrAdmin

class ProductListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsWarehouseManagerOrAdmin()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = product_services.create_product(serializer.validated_data)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        # We can implement list caching
        cache_key = 'products:list'
        
        # Check if query filters are active. If active, bypass cache
        has_filters = any(k in request.query_params for k in ['category_id', 'is_active', 'min_price', 'max_price', 'search', 'page'])
        
        if not has_filters:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)

        queryset = Product.objects.all().order_by('id')
        filter_set = ProductFilter(request.query_params, queryset=queryset)
        if filter_set.is_valid():
            queryset = filter_set.qs

        from core.pagination import StandardResultsPagination
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            if not has_filters:
                cache.set(cache_key, response_data, timeout=600) # 10 min cache
            return Response(response_data)

        serializer = ProductSerializer(queryset, many=True)
        if not has_filters:
            cache.set(cache_key, serializer.data, timeout=600)
        return Response(serializer.data)

class ProductDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['PUT', 'DELETE']:
            return [IsWarehouseManagerOrAdmin()]
        return [IsAuthenticated()]

    def get(self, request, pk, *args, **kwargs):
        product_detail = product_services.get_product_with_inventory(pk)
        return Response(product_detail, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        serializer = ProductSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = product_services.update_product(pk, serializer.validated_data)
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        product_services.delete_product(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
