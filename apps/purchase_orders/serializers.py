from rest_framework import serializers
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from apps.products.serializers import ProductSerializer

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ('id', 'product_id', 'product_sku', 'product_name', 'quantity_ordered', 'quantity_received', 'unit_price', 'total_price', 'created_at', 'updated_at')

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True, default=None)

    class Meta:
        model = PurchaseOrder
        fields = ('id', 'po_number', 'supplier_id', 'supplier_name', 'warehouse_id', 'warehouse_name', 'status', 'total_amount', 'expected_delivery_date', 'actual_delivery_date', 'created_by_name', 'approved_by_name', 'notes', 'items', 'created_at', 'updated_at')

class PurchaseOrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity_ordered = serializers.IntegerField(required=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    def validate_quantity_ordered(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity ordered must be greater than zero.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price must be non-negative.")
        return value

class PurchaseOrderCreateSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True)
    warehouse_id = serializers.IntegerField(required=True)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = PurchaseOrderItemCreateSerializer(many=True, required=True, allow_empty=False)

class PurchaseOrderItemReceiveSerializer(serializers.Serializer):
    po_item_id = serializers.IntegerField(required=True)
    quantity_received = serializers.IntegerField(required=True)

    def validate_quantity_received(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity received must be greater than zero.")
        return value

class PurchaseOrderReceiveSerializer(serializers.Serializer):
    items = PurchaseOrderItemReceiveSerializer(many=True, required=True, allow_empty=False)
    actual_delivery_date = serializers.DateField(required=False, allow_null=True)
