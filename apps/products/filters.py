import django_filters
from django.db.models import Q
from apps.products.models import Product

class ProductFilter(django_filters.FilterSet):
    category_id = django_filters.NumberFilter(field_name='category_id', lookup_expr='exact')
    is_active = django_filters.BooleanFilter(field_name='is_active', lookup_expr='exact')
    min_price = django_filters.NumberFilter(field_name='unit_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='unit_price', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Product
        fields = ['category_id', 'is_active', 'min_price', 'max_price', 'search']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value)
        )
