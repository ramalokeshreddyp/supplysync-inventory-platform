from rest_framework import serializers
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType

class InventorySerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.warehouse_code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = Inventory
        fields = ('id', 'product_id', 'product_sku', 'product_name', 'warehouse_id', 'warehouse_code', 'warehouse_name', 'quantity_available', 'quantity_reserved', 'quantity_damaged', 'last_updated_at')

class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.warehouse_code', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.full_name', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = ('id', 'product_id', 'product_sku', 'warehouse_id', 'warehouse_code', 'transaction_type', 'quantity', 'reference_id', 'performed_by_name', 'notes', 'created_at')

class InventoryAdjustSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    warehouse_id = serializers.IntegerField(required=True)
    transaction_type = serializers.ChoiceField(choices=TransactionType.choices, required=True)
    quantity = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

class InventoryTransferSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    source_warehouse_id = serializers.IntegerField(required=True)
    destination_warehouse_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate(self, data):
        if data['source_warehouse_id'] == data['destination_warehouse_id']:
            raise serializers.ValidationError("Source and destination warehouses must be different.")
        return data
