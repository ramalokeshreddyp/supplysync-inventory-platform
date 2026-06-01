from django.db import models
from core.models import BaseModel
from apps.suppliers.models import Supplier
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from django.conf import settings

class PurchaseOrderStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    ORDERED = 'ORDERED', 'Ordered'
    PARTIALLY_RECEIVED = 'PARTIALLY_RECEIVED', 'Partially Received'
    RECEIVED = 'RECEIVED', 'Received'
    CANCELLED = 'CANCELLED', 'Cancelled'

class PurchaseOrder(BaseModel):
    po_number = models.CharField(max_length=30, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='purchase_orders')
    status = models.CharField(max_length=30, choices=PurchaseOrderStatus.choices, default=PurchaseOrderStatus.DRAFT)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='created_purchase_orders'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_purchase_orders'
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'purchase_orders'

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} ({self.status})"

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_order_items')
    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchase_order_items'

    def save(self, *args, **kwargs):
        # Auto calculate total_price
        self.total_price = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.sku} ({self.quantity_ordered}) for {self.purchase_order.po_number}"
