from rest_framework import serializers
from apps.categories.models import Category

class CategorySerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(required=False, allow_blank=False, max_length=20)
    name = serializers.CharField(required=True, allow_blank=False, max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    parent_category_id = serializers.IntegerField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = Category
        fields = ('id', 'category_code', 'name', 'description', 'parent_category_id', 'created_at', 'updated_at')

class CategoryTreeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    category_code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        # In this serializer, obj could be a Category model or a dictionary (pre-built category tree from cache)
        if isinstance(obj, dict):
            return obj.get('children', [])
        # Fallback if obj is Category model
        serializer = CategoryTreeSerializer(obj.children.all(), many=True)
        return serializer.data
