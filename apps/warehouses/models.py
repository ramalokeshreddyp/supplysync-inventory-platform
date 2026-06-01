from django.db import models
from core.models import BaseModel
from core.utils import generate_random_code

class Warehouse(BaseModel):
    warehouse_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    location = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    capacity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'warehouses'

    def save(self, *args, **kwargs):
        if not self.warehouse_code:
            # Generate a code that is unique
            code = generate_random_code("WH", length=6)
            while Warehouse.all_objects.filter(warehouse_code=code).exists():
                code = generate_random_code("WH", length=6)
            self.warehouse_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.warehouse_code})"
