from rest_framework import serializers
from apps.suppliers.models import Supplier

class SupplierSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(required=False, allow_blank=False, max_length=20)
    name = serializers.CharField(required=True, allow_blank=False, max_length=200)
    contact_person = serializers.CharField(required=True, allow_blank=False, max_length=150)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True, allow_blank=False, max_length=20)
    address = serializers.CharField(required=True, allow_blank=False)
    city = serializers.CharField(required=True, allow_blank=False, max_length=100)
    state = serializers.CharField(required=True, allow_blank=False, max_length=100)
    pincode = serializers.CharField(required=True, allow_blank=False, max_length=10)
    gstin = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20)
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Supplier
        fields = ('id', 'supplier_code', 'name', 'contact_person', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'gstin', 'is_active', 'created_at', 'updated_at')
