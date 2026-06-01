from apps.categories.models import Category
from core.exceptions import DuplicateResourceException, ResourceNotFoundException
from django.core.cache import cache
from core.constants import CATEGORY_TREE_CACHE_TTL
from collections import defaultdict

def create_category(data: dict) -> Category:
    code = data.get('category_code')
    if code:
        if Category.all_objects.filter(category_code=code).exists():
            raise DuplicateResourceException(
                detail="Category code already exists.",
                code="DUPLICATE_RESOURCE"
            )
            
    parent_id = data.get('parent_category_id')
    parent = None
    if parent_id:
        try:
            parent = Category.objects.get(id=parent_id)
        except Category.DoesNotExist:
            raise ResourceNotFoundException("Parent category not found.")

    category = Category.objects.create(
        category_code=code or '',
        name=data['name'],
        description=data.get('description'),
        parent_category=parent
    )
    
    # Invalidate categories tree cache
    cache.delete('categories:tree')
    return category

def get_category_tree() -> list:
    cache_key = 'categories:tree'
    cached = cache.get(cache_key)
    if cached:
        return cached

    all_cats = list(Category.objects.all())
    
    parent_map = defaultdict(list)
    roots = []
    for cat in all_cats:
        if cat.parent_category_id is None:
            roots.append(cat)
        else:
            parent_map[cat.parent_category_id].append(cat)

    def build_node(cat):
        return {
            "id": cat.id,
            "category_code": cat.category_code,
            "name": cat.name,
            "description": cat.description,
            "children": [build_node(child) for child in parent_map[cat.id]]
        }

    tree = [build_node(root) for root in roots]
    cache.set(cache_key, tree, timeout=CATEGORY_TREE_CACHE_TTL)
    return tree
