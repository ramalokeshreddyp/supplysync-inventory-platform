from django.db import models
from core.models import BaseModel
from core.utils import generate_random_code
from apps.categories.models import Category

class Product(BaseModel):
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_of_measure = models.CharField(max_length=20)
    reorder_level = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'products'

    def save(self, *args, **kwargs):
        if not self.sku:
            cat_code = self.category.category_code
            prefix = f"SKU-{cat_code}"
            code = generate_random_code(prefix, length=8)
            while Product.all_objects.filter(sku=code).exists():
                code = generate_random_code(prefix, length=8)
            self.sku = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"
