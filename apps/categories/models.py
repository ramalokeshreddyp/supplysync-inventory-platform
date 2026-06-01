from django.db import models
from core.models import BaseModel
from core.utils import generate_random_code

class Category(BaseModel):
    category_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    parent_category = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )

    class Meta:
        db_table = 'categories'

    def save(self, *args, **kwargs):
        if not self.category_code:
            code = generate_random_code("CAT", length=6)
            while Category.all_objects.filter(category_code=code).exists():
                code = generate_random_code("CAT", length=6)
            self.category_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.category_code})"
