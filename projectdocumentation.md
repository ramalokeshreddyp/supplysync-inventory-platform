# Project Documentation — SupplySync

This document provides comprehensive documentation of modules, APIs, services, tasks, caches, and testing strategies for the SupplySync project.

## 1. Goals & Objectives
- Accurate inventory management across warehouses
- Atomic and auditable inventory transactions
- Reliable order lifecycles for purchase and sales orders
- Responsive dashboards and alerts for low-stock
- Scalable background processing for event-driven side-effects

## 2. Models (summary)
- `User` (apps/accounts/models.py) — custom AbstractBaseUser with roles: ADMIN, WAREHOUSE_MANAGER, PROCUREMENT_MANAGER, STAFF. `db_table='users'`.
- `Warehouse` (`apps/warehouses/models.py`) — `db_table='warehouses'`.
- `Category` (`apps/categories/models.py`) — self-referential parent-child, `db_table='categories'`.
- `Product` (`apps/products/models.py`) — `db_table='products'`.
- `Inventory` (`apps/inventory/models.py`) — per product-per warehouse current state; unique_together `('product','warehouse')`; `db_table='inventory'`.
- `InventoryTransaction` (`apps/inventory/models.py`) — append-only audit log, `db_table='inventory_transactions'` (no soft-delete).
- `Supplier`, `PurchaseOrder`, `PurchaseOrderItem`, `SalesOrder`, `SalesOrderItem` — as per project requirements with explicit `db_table` names.

## 3. Service Layer (pattern)
- Services live in `apps/<app>/services.py`.
- Responsibilities:
  - Enforce business rules and status transitions
  - Apply `transaction.atomic()` where needed
  - Use `select_for_update()` for inventory row locking
  - Read/write cache keys and manage TTLs
  - Enqueue Celery tasks in `transaction.on_commit()` callbacks

### Example: `apps/inventory/services.py`
- `adjust_inventory(data: dict, performed_by_user_id: int) -> InventoryTransaction`
- `transfer_inventory(data: dict, performed_by_user_id: int) -> dict`
- `get_low_stock_alerts() -> list`
- `check_and_publish_low_stock_alert(product_id: int, warehouse_id: int) -> None`

## 4. Views & Serializers
- Views are thin and use class-based views (APIViews/generic) to parse requests and delegate to services.
- Serializers handle field-level validation only (min/max, non-null, password strength via `validate_password_strength` in `apps/accounts/validators.py`).
- No business logic inside serializers — they never mutate other models or orchestrate transactions.

## 5. Celery Tasks
- Tasks are idempotent and retryable with exponential backoff when appropriate.
- Key tasks:
  - `apps/inventory.tasks.process_inventory_updated_event(product_id, warehouse_id, type, quantity)`
  - `apps/inventory.tasks.process_inventory_transfer_event(product_id, source_wh, dest_wh, qty)`
  - `apps/purchase_orders.tasks.process_purchase_order_received_event(po_id, received_by)`
  - `apps/sales_orders.tasks.process_sales_order_created_event(order_id, created_by)`
  - Periodic: `auto_invalidate_low_stock_cache`, `generate_daily_operations_summary`

## 6. Caching
- Central TTL constants in `core/constants.py`.
- Cache key patterns:
  - `products:detail:{id}` — TTL 10 minutes
  - `products:list` — TTL 10 minutes
  - `categories:tree` — TTL 30 minutes
  - `warehouses:detail:{id}` — TTL 15 minutes
  - `warehouses:list` — TTL 15 minutes
  - `inventory:low-stock` — TTL 5 minutes
  - `suppliers:detail:{id}` — TTL 20 minutes
  - `reports:dashboard` — TTL 10 minutes
- All cache reads/writes occur in services.
- Invalidation triggered after successful DB commits and periodically by Celery tasks.

## 7. Rate limiting (login)
- Implemented in `core/throttles.py` with key `rate-limit:login:{ip}` and TTL 900 seconds.
- Only failed login attempts increment the counter via `cache.add()` then `cache.incr()` for atomic initialization+increment behavior.
- Successful login clears the key.

## 8. Error handling
- Unified error responses via `core/exceptions.custom_exception_handler` returning:
```
{
  "timestamp": "2025-07-15T10:30:00.000Z",
  "status": 400,
  "error_code": "VALIDATION_FAILED",
  "message": "string",
  "path": "/api/v1/products/",
  "errors": []
}
```
- Custom exception classes: `ResourceNotFoundException`, `DuplicateResourceException`, `InsufficientInventoryException`, `InvalidOperationException`.

## 9. Tests
- `pytest.ini` configures tests to use `supplysync.settings.testing`.
- Tests under `tests/` are divided by app. Tests cover both services (unit tests) and views (integration tests with APIClient).
- Fixtures are in `tests/conftest.py` and include sample users, warehouses, products, suppliers, and inventory.
- Celery is run in eager mode for testing.

## 10. API documentation
- drf-spectacular provides OpenAPI schema at `/api/schema/` and UI at `/api/schema/swagger-ui/`.
- Use `@extend_schema` where view actions aren't self-evident (submit/approve/receive/dispatch/etc.).

## 11. Extending the project
- To add a new domain area: create an app under `apps/`, follow the `models/serializers/services/tasks/views/urls` pattern, write migrations, add to `INSTALLED_APPS`, and add tests.
- Use service functions to encapsulate business rules and keep views thin.

## 12. Common troubleshooting
- Celery cannot connect to Redis in Docker: ensure `REDIS_URL` references the service name `redis` in Docker Compose (e.g., `redis://redis:6379/1`).
- Tests failing due to select_for_update: run tests with `transaction=True` marker where necessary or adjust to use the provided fixtures.

## 13. Appendix: Important files
- `supplysync/settings/base.py` — main configuration (CACHES, CELERY, REST_FRAMEWORK)
- `core/constants.py` — TTLs and cache key patterns
- `apps/inventory/services.py` — core inventory logic
- `apps/purchase_orders/services.py` — PO lifecycle logic
- `apps/sales_orders/services.py` — SO lifecycle logic
- `apps/*/tasks.py` — Celery tasks
- `docker-compose.yml` — infra services

