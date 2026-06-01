from rest_framework import serializers
from apps.sales_orders.models import SalesOrder, SalesOrderItem, SalesOrderStatus

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ('id', 'product_id', 'product_sku', 'product_name', 'quantity', 'unit_price', 'total_price', 'created_at', 'updated_at')

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = SalesOrder
        fields = ('id', 'order_number', 'customer_name', 'customer_email', 'customer_phone', 'shipping_address', 'warehouse_id', 'warehouse_name', 'status', 'total_amount', 'dispatched_at', 'delivered_at', 'created_by_name', 'notes', 'items', 'created_at', 'updated_at')

class SalesOrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

class SalesOrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(required=True, allow_blank=False, max_length=200)
    customer_email = serializers.EmailField(required=True)
    customer_phone = serializers.CharField(required=True, allow_blank=False, max_length=20)
    shipping_address = serializers.CharField(required=True, allow_blank=False)
    warehouse_id = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = SalesOrderItemCreateSerializer(many=True, required=True, allow_empty=False)
