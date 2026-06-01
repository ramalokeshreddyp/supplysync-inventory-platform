from apps.products.models import Product
from apps.categories.models import Category
from apps.inventory.models import Inventory
from core.exceptions import DuplicateResourceException, ResourceNotFoundException
from django.core.cache import cache
from core.constants import PRODUCT_DETAIL_CACHE_TTL, PRODUCT_LIST_CACHE_TTL

def create_product(data: dict) -> Product:
    sku = data.get('sku')
    if sku:
        if Product.all_objects.filter(sku=sku).exists():
            raise DuplicateResourceException(
                detail="Product SKU already exists.",
                code="DUPLICATE_RESOURCE"
            )

    try:
        category = Category.objects.get(id=data['category_id'])
    except Category.DoesNotExist:
        raise ResourceNotFoundException("Category not found.")

    product = Product.objects.create(
        sku=sku or '',
        name=data['name'],
        description=data.get('description'),
        category=category,
        unit_price=data['unit_price'],
        unit_of_measure=data['unit_of_measure'],
        reorder_level=data.get('reorder_level', 0),
        is_active=data.get('is_active', True)
    )

    # Invalidate products list cache
    cache.delete('products:list')
    return product

def get_product_with_inventory(product_id: int) -> dict:
    cache_key = f'products:detail:{product_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        product = Product.objects.select_related('category').get(id=product_id)
    except Product.DoesNotExist:
        raise ResourceNotFoundException("Product not found.")

    inventory_records = Inventory.objects.filter(product=product).select_related('warehouse')
    inventory_list = []
    for record in inventory_records:
        inventory_list.append({
            "warehouse_id": record.warehouse.id,
            "warehouse_name": record.warehouse.name,
            "quantity_available": record.quantity_available,
            "quantity_reserved": record.quantity_reserved
        })

    result = {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category_id": product.category.id,
        "category_name": product.category.name,
        "unit_price": str(product.unit_price),
        "unit_of_measure": product.unit_of_measure,
        "reorder_level": product.reorder_level,
        "is_active": product.is_active,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
        "inventory_by_warehouse": inventory_list
    }

    cache.set(cache_key, result, timeout=PRODUCT_DETAIL_CACHE_TTL)
    return result

def update_product(product_id: int, data: dict) -> Product:
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ResourceNotFoundException("Product not found.")

    if 'category_id' in data:
        try:
            product.category = Category.objects.get(id=data['category_id'])
        except Category.DoesNotExist:
            raise ResourceNotFoundException("Category not found.")

    for field in ['name', 'description', 'unit_price', 'unit_of_measure', 'reorder_level', 'is_active']:
        if field in data:
            setattr(product, field, data[field])

    product.save()

    # Invalidate caches
    cache.delete(f'products:detail:{product.id}')
    cache.delete('products:list')
    return product

def delete_product(product_id: int) -> None:
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ResourceNotFoundException("Product not found.")

    product.delete()

    # Invalidate caches
    cache.delete(f'products:detail:{product_id}')
    cache.delete('products:list')
