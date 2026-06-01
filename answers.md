1) Handling concurrent inventory updates and why select_for_update() is necessary

I use database transactions and row-level locks to guarantee correctness under concurrency. In `apps/inventory/services.py` all mutating operations (adjust_inventory, transfer_inventory, create/reserve flows) run inside `transaction.atomic()` and obtain locks on the affected `Inventory` rows using `select_for_update()` before reading/modifying quantities. This ensures a single transaction holds the row lock while it computes and writes new quantities; concurrent transactions will wait on the lock and thus observe a consistent, serialized update.

Without `select_for_update()` two concurrent requests can both read the same available quantity, both decide the stock is sufficient, and both deduct—resulting in negative or oversold stock (race conditions). `select_for_update()` prevents lost updates and enforces the sequential ordering required for correctness.

I also avoid deadlocks by locking related rows in a deterministic order (see `transfer_inventory` which sorts warehouse IDs before locking), and I use `transaction.on_commit()` to dispatch side-effects (Celery tasks) only after the DB commit.

2) Design decision to use Celery for event tasks (e.g., process_inventory_updated_event)

Pros:
- Asynchronous side-effects (notifications, low-stock checks, report generation) do not block request latency; the HTTP response returns quickly.
- Retries with exponential backoff are supported; tasks in `apps/*/tasks.py` use `@shared_task(bind=True, max_retries=3)` and `self.retry()` on failure.
- Decouples event producers (service layer) from consumers; tasks can be scaled independently.
- Periodic work (cache invalidation, daily summaries) is handled by Celery Beat reliably.

Cons / trade-offs:
- Operational complexity: requires a broker (Redis) and running worker processes. Docker Compose includes `redis`, `celery_worker`, and `celery_beat` for this reason.
- Slight delay in eventual consistency for side-effects (e.g., background analytics) compared to synchronous processing.
- Tests need configuration to run tasks synchronously; `testing.py` sets Celery to eager mode so unit tests remain deterministic.

I chose Celery because the system must be resilient under load and background tasks must be retryable and idempotent—requirements that match Celery's strengths.

3) Redis caching strategy and invalidation for dashboard and low-stock alerts

Cache keys and TTLs are defined as constants in `core/constants.py` (e.g., `INVENTORY_LOW_STOCK_CACHE_TTL`, `REPORT_DASHBOARD_CACHE_TTL`). The code reads/writes cache inside service functions (not views) following the pattern in `apps/inventory/services.py` and reporting services:
- Low-stock alerts: `get_low_stock_alerts()` caches results under key `inventory:low-stock` with TTL 5 minutes. Any inventory-changing operation calls `cache.delete('inventory:low-stock')` after a successful change (see `adjust_inventory`, `transfer_inventory`, and `check_and_publish_low_stock_alert`). Celery periodic task `auto_invalidate_low_stock_cache` also clears the key every 5 minutes.
- Dashboard: `reports:dashboard` is cached for 10 minutes (constant). Service-layer updates that materially affect dashboard data invalidate the key after commit.

Important patterns used:
- Centralized TTLs in `core/constants.py` (no magic numbers scattered in code).
- Cache operations live in the service layer, so business logic controls when values are stale and when they must be invalidated.
- `transaction.on_commit()` is used to schedule tasks and cache-invalidation only after the DB commit to avoid premature invalidation on rollback.

4) Benefits of separating business logic into `services.py` (away from views/serializers)

Separation yields multiple concrete benefits:
- Testability: services are plain functions with explicit inputs/outputs, easy to unit-test (mocks for cache/Celery). The test suite exercises services directly in `tests/*/test_services.py`.
- Single responsibility: views handle HTTP concerns (auth, input parsing) and serializers validate input; services enforce status transitions, transactions, cache and task orchestration.
- Consistency: `transaction.atomic()` and `select_for_update()` live in services where transactional boundaries belong; side-effects use `transaction.on_commit()` consistently.
- Reuse: CLI scripts, management commands, and other views can call the same service functions without duplicating logic.
- Cleaner serializers: no business logic in serializers reduces accidental side-effects during validation.

5) Redis-based rate limiter for the login endpoint and race handling

Implementation details (see `core/throttles.py` and `apps/accounts/views.py`):
- Key format: `rate-limit:login:{ip_address}`. TTL = 900 seconds (15 minutes).
- Only failed login attempts increment the counter: in `LoginView.post()`, on successful auth `LoginRateLimitThrottle.clear_failed_attempts(ip)` deletes the key; on failure the view calls `LoginRateLimitThrottle.increment_failed_attempts(ip)` before re-raising.
- `increment_failed_attempts` uses `cache.add(key, 1, timeout=900)` to set the counter atomically if absent (and set TTL), and falls back to `cache.incr(key)` when the key already exists. Redis `INCR` is atomic, so concurrent increments are safe; `cache.add` ensures the TTL is set on the first write to avoid keys without expiry.
- The throttle's `allow_request()` reads the counter and raises `Throttled` when the count >= 5.

This approach avoids counting successful logins and ensures the first failed attempt initializes the key with an expiry. Using `cache.add` followed by `INCR` prevents a race where two concurrent first-failure requests might create the key without TTL; Redis-backed `INCR` operations remain atomic and consistent for concurrent increments.

---

Files containing the implementations referenced above:
- `apps/inventory/services.py`
- `apps/inventory/tasks.py`
- `apps/accounts/views.py`
- `core/throttles.py`
- `core/constants.py`
- `supplysync/celery.py`

