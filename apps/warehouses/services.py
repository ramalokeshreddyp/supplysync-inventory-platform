from django.db import models
from apps.warehouses.models import Warehouse
from apps.inventory.models import Inventory
from core.exceptions import DuplicateResourceException, ResourceNotFoundException, InvalidOperationException
from django.core.cache import cache
from core.constants import WAREHOUSE_DETAIL_CACHE_TTL, WAREHOUSE_LIST_CACHE_TTL

def create_warehouse(data: dict) -> Warehouse:
    code = data.get('warehouse_code')
    if code:
        if Warehouse.all_objects.filter(warehouse_code=code).exists():
            raise DuplicateResourceException(
                detail="Warehouse code already exists.",
                code="DUPLICATE_RESOURCE"
            )
    
    warehouse = Warehouse.objects.create(
        warehouse_code=code or '',
        name=data['name'],
        location=data['location'],
        city=data['city'],
        state=data['state'],
        pincode=data['pincode'],
        capacity=data['capacity'],
        is_active=data.get('is_active', True)
    )
    # Invalidate caches
    cache.delete('warehouses:list')
    return warehouse

def get_warehouse_with_summary(warehouse_id: int) -> dict:
    cache_key = f'warehouses:detail:{warehouse_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise ResourceNotFoundException("Warehouse not found.")

    inventory_records = Inventory.objects.filter(warehouse=warehouse)
    total_distinct_products = inventory_records.values('product').distinct().count()
    total_quantity_available = inventory_records.aggregate(total=models.Sum('quantity_available'))['total'] or 0

    result = {
        "warehouse": warehouse,
        "total_distinct_products": total_distinct_products,
        "total_quantity_available": total_quantity_available
    }
    
    # Store clean serializable details in cache
    # But wait! Since Django models are not directly serializable in JSON cache, we should either cache the raw dictionary of serialized data or a dict of primitives.
    # In Django, let's cache the structure with the model's serialized attributes.
    # We will serialize it in the service or just cache the serialized output. Let's cache the primitive representation!
    # That is much safer for Redis cache, to avoid Pickling errors or lazy database access.
    # Let's do that:
    primitive_result = {
        "id": warehouse.id,
        "warehouse_code": warehouse.warehouse_code,
        "name": warehouse.name,
        "location": warehouse.location,
        "city": warehouse.city,
        "state": warehouse.state,
        "pincode": warehouse.pincode,
        "capacity": warehouse.capacity,
        "is_active": warehouse.is_active,
        "created_at": warehouse.created_at.isoformat(),
        "updated_at": warehouse.updated_at.isoformat(),
        "total_distinct_products": total_distinct_products,
        "total_quantity_available": total_quantity_available
    }
    cache.set(cache_key, primitive_result, timeout=WAREHOUSE_DETAIL_CACHE_TTL)
    return primitive_result

def update_warehouse(warehouse_id: int, data: dict) -> Warehouse:
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise ResourceNotFoundException("Warehouse not found.")

    # warehouse_code cannot be changed after creation.
    if 'warehouse_code' in data and data['warehouse_code'] != warehouse.warehouse_code:
        raise InvalidOperationException(
            detail="Warehouse code cannot be changed after creation.",
            code="WAREHOUSE_CODE_IMMUTABLE"
        )

    for field in ['name', 'location', 'city', 'state', 'pincode', 'capacity', 'is_active']:
        if field in data:
            setattr(warehouse, field, data[field])
            
    warehouse.save()
    
    # Invalidate cache
    cache.delete(f'warehouses:detail:{warehouse.id}')
    cache.delete('warehouses:list')
    
    return warehouse

def delete_warehouse(warehouse_id: int) -> None:
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise ResourceNotFoundException("Warehouse not found.")

    # A warehouse cannot be deleted if it has any Inventory record with quantity_available > 0 or quantity_reserved > 0.
    has_active_inventory = Inventory.objects.filter(
        warehouse=warehouse
    ).filter(
        models.Q(quantity_available__gt=0) | models.Q(quantity_reserved__gt=0)
    ).exists()

    if has_active_inventory:
        raise DuplicateResourceException(
            detail="Warehouse has active inventory.",
            code="WAREHOUSE_HAS_ACTIVE_INVENTORY"
        )

    warehouse.delete()
    
    # Invalidate cache
    cache.delete(f'warehouses:detail:{warehouse_id}')
    cache.delete('warehouses:list')
