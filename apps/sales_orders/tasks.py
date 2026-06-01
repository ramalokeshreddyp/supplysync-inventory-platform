import logging
import datetime
from celery import shared_task
from django.utils import timezone
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderStatus
from apps.sales_orders.models import SalesOrder, SalesOrderStatus

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_sales_order_created_event(self, order_id: int, created_by_user_id: int):
    try:
        logger.info(f"EVENT [sales-order-created]: order_id={order_id}, created_by={created_by_user_id}")
    except Exception as exc:
        countdown = 2 ** self.request.retries
        logger.error(f"Error processing sales order creation event, retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)

@shared_task(bind=True, max_retries=3)
def process_sales_order_cancelled_event(self, order_id: int):
    try:
        logger.info(f"EVENT [sales-order-cancelled]: order_id={order_id}")
    except Exception as exc:
        countdown = 2 ** self.request.retries
        logger.error(f"Error processing sales order cancellation event, retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)

@shared_task
def generate_daily_operations_summary():
    today = datetime.date.today()
    today_str = today.isoformat()
    
    # Counts
    new_pos = PurchaseOrder.all_objects.filter(created_at__date=today).count()
    pos_received = PurchaseOrder.all_objects.filter(status=PurchaseOrderStatus.RECEIVED, updated_at__date=today).count()
    
    new_sos = SalesOrder.all_objects.filter(created_at__date=today).count()
    orders_dispatched = SalesOrder.all_objects.filter(status__in=[SalesOrderStatus.DISPATCHED, SalesOrderStatus.DELIVERED], dispatched_at__date=today).count()
    orders_delivered = SalesOrder.all_objects.filter(status=SalesOrderStatus.DELIVERED, delivered_at__date=today).count()

    logger.info(
        f"DAILY SUMMARY: Date={today_str}, New POs={new_pos}, POs Received={pos_received}, "
        f"New Sales Orders={new_sos}, Orders Dispatched={orders_dispatched}, Orders Delivered={orders_delivered}"
    )
