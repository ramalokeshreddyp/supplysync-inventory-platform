from rest_framework import serializers
from apps.warehouses.models import Warehouse

class WarehouseSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(required=False, allow_blank=False, max_length=20)
    name = serializers.CharField(required=True, allow_blank=False, max_length=150)
    location = serializers.CharField(required=True, allow_blank=False)
    city = serializers.CharField(required=True, allow_blank=False, max_length=100)
    state = serializers.CharField(required=True, allow_blank=False, max_length=100)
    pincode = serializers.CharField(required=True, allow_blank=False, max_length=10)
    capacity = serializers.IntegerField(required=True)
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Warehouse
        fields = ('id', 'warehouse_code', 'name', 'location', 'city', 'state', 'pincode', 'capacity', 'is_active', 'created_at', 'updated_at')

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than zero.")
        return value
