from rest_framework import serializers
from apps.products.models import Product
from apps.categories.models import Category

class ProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(required=False, allow_blank=False, max_length=50)
    name = serializers.CharField(required=True, allow_blank=False, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    category_id = serializers.IntegerField(required=True, write_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    unit_of_measure = serializers.CharField(required=True, allow_blank=False, max_length=20)
    reorder_level = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Product
        fields = ('id', 'sku', 'name', 'description', 'category_id', 'category_name', 'unit_price', 'unit_of_measure', 'reorder_level', 'is_active', 'created_at', 'updated_at')

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price must be non-negative.")
        return value

    def validate_reorder_level(self, value):
        if value < 0:
            raise serializers.ValidationError("Reorder level must be non-negative.")
        return value
