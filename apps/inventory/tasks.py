import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_inventory_updated_event(self, product_id: int, warehouse_id: int, transaction_type: str, quantity: int):
    try:
        logger.info(f"EVENT [inventory-updated]: product_id={product_id}, warehouse_id={warehouse_id}, type={transaction_type}, qty={quantity}")
        
        # Import dynamically to avoid circular import issues
        from apps.inventory.services import check_and_publish_low_stock_alert
        check_and_publish_low_stock_alert(product_id, warehouse_id)
    except Exception as exc:
        countdown = 2 ** self.request.retries
        logger.error(f"Error processing inventory update event, retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)

@shared_task(bind=True, max_retries=3)
def process_inventory_transfer_event(self, product_id: int, source_warehouse_id: int, destination_warehouse_id: int, quantity: int):
    try:
        logger.info(f"EVENT [inventory-transfer-initiated]: product_id={product_id}, from={source_warehouse_id}, to={destination_warehouse_id}, qty={quantity}")
        
        # Check low stock in both source and destination
        from apps.inventory.services import check_and_publish_low_stock_alert
        check_and_publish_low_stock_alert(product_id, source_warehouse_id)
        check_and_publish_low_stock_alert(product_id, destination_warehouse_id)
    except Exception as exc:
        countdown = 2 ** self.request.retries
        logger.error(f"Error processing inventory transfer event, retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)

@shared_task
def auto_invalidate_low_stock_cache():
    logger.info("Executing periodic task auto_invalidate_low_stock_cache")
    cache.delete('inventory:low-stock')
