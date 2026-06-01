from django.db import models
from core.models import BaseModel
from core.utils import generate_random_code

class Supplier(BaseModel):
    supplier_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    gstin = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'suppliers'

    def save(self, *args, **kwargs):
        if not self.supplier_code:
            code = generate_random_code("SUP", length=6)
            while Supplier.all_objects.filter(supplier_code=code).exists():
                code = generate_random_code("SUP", length=6)
            self.supplier_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.supplier_code})"
