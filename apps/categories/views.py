from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.categories.serializers import CategorySerializer, CategoryTreeSerializer
from apps.categories import services as category_services
from apps.categories.models import Category
from core.permissions import IsAdminUser

class CategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = category_services.create_category(serializer.validated_data)
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        # Optional: paginate categories
        queryset = Category.objects.all().order_by('id')
        from core.pagination import StandardResultsPagination
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = CategorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = CategorySerializer(queryset, many=True)
        return Response(serializer.data)

class CategoryTreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tree_data = category_services.get_category_tree()
        # Since it's nested dictionary data, we can just return it in response directly
        return Response(tree_data, status=status.HTTP_200_OK)
