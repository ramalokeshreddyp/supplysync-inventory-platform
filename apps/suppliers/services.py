from apps.suppliers.models import Supplier
from core.exceptions import DuplicateResourceException, ResourceNotFoundException
from django.db.models import QuerySet
from django.core.cache import cache
from core.constants import SUPPLIER_DETAIL_CACHE_TTL

def create_supplier(data: dict) -> Supplier:
    code = data.get('supplier_code')
    if code:
        if Supplier.all_objects.filter(supplier_code=code).exists():
            raise DuplicateResourceException(
                detail="Supplier code already exists.",
                code="DUPLICATE_RESOURCE"
            )

    supplier = Supplier.objects.create(
        supplier_code=code or '',
        name=data['name'],
        contact_person=data['contact_person'],
        email=data['email'],
        phone=data['phone'],
        address=data['address'],
        city=data['city'],
        state=data['state'],
        pincode=data['pincode'],
        gstin=data.get('gstin'),
        is_active=data.get('is_active', True)
    )
    return supplier

def update_supplier(supplier_id: int, data: dict) -> Supplier:
    try:
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        raise ResourceNotFoundException("Supplier not found.")

    if 'supplier_code' in data and data['supplier_code'] != supplier.supplier_code:
        if Supplier.all_objects.filter(supplier_code=data['supplier_code']).exclude(id=supplier_id).exists():
            raise DuplicateResourceException(
                detail="Supplier code already exists.",
                code="DUPLICATE_RESOURCE"
            )
            
    for field in ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'gstin', 'is_active']:
        if field in data:
            setattr(supplier, field, data[field])
            
    supplier.save()
    cache.delete(f"suppliers:detail:{supplier_id}")
    return supplier

def get_supplier_by_id(supplier_id: int) -> Supplier:
    cache_key = f"suppliers:detail:{supplier_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        raise ResourceNotFoundException("Supplier not found.")

    cache.set(cache_key, supplier, timeout=SUPPLIER_DETAIL_CACHE_TTL)
    return supplier

def list_suppliers(filters: dict, page: int, page_size: int) -> QuerySet:
    qs = Supplier.objects.filter(**filters)
    # Apply pagination slicing
    start = (page - 1) * page_size
    end = start + page_size
    return qs[start:end]

def delete_supplier(supplier_id: int) -> None:
    try:
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        raise ResourceNotFoundException("Supplier not found.")

    supplier.delete()
    cache.delete(f"suppliers:detail:{supplier_id}")
