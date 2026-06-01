from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from core.models import BaseModel
from apps.accounts.managers import UserManager

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    WAREHOUSE_MANAGER = 'WAREHOUSE_MANAGER', 'Warehouse Manager'
    PROCUREMENT_MANAGER = 'PROCUREMENT_MANAGER', 'Procurement Manager'
    STAFF = 'STAFF', 'Staff'

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=30, choices=UserRole.choices, default=UserRole.STAFF)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.email} ({self.role})"
