from django.db import models
from core.models import BaseModel
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from django.conf import settings

class SalesOrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    PROCESSING = 'PROCESSING', 'Processing'
    DISPATCHED = 'DISPATCHED', 'Dispatched'
    DELIVERED = 'DELIVERED', 'Delivered'
    CANCELLED = 'CANCELLED', 'Cancelled'
    RETURNED = 'RETURNED', 'Returned'

class SalesOrder(BaseModel):
    order_number = models.CharField(max_length=30, unique=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    shipping_address = models.TextField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='sales_orders')
    status = models.CharField(max_length=30, choices=SalesOrderStatus.choices, default=SalesOrderStatus.PENDING)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_sales_orders')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'sales_orders'

    def __str__(self):
        return f"{self.order_number} - {self.customer_name} ({self.status})"

class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sales_order_items')
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sales_order_items'

    def save(self, *args, **kwargs):
        # Auto calculate total_price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.sku} ({self.quantity}) for {self.sales_order.order_number}"
