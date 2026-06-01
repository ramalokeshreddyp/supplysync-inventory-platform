from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
from rest_framework.exceptions import Throttled

class LoginRateLimitThrottle(BaseThrottle):
    def get_ident(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def allow_request(self, request, view):
        self.ip_address = self.get_ident(request)
        self.key = f"rate-limit:login:{self.ip_address}"
        
        count = cache.get(self.key)
        if count is not None and int(count) >= 5:
            # We raise a custom throttled error here or return False
            raise Throttled(detail="Too many failed login attempts. Please try again later.")
        return True

    @staticmethod
    def increment_failed_attempts(ip_address):
        key = f"rate-limit:login:{ip_address}"
        # We need to set TTL of 900 seconds on the first failed attempt.
        # Use cache.add to set value to 1 with 900s timeout if it doesn't exist.
        # Otherwise, increment.
        is_new = cache.add(key, 1, timeout=900)
        if not is_new:
            try:
                cache.incr(key)
            except ValueError:
                # If there was a type mismatch or other issue
                cache.set(key, 1, timeout=900)

    @staticmethod
    def clear_failed_attempts(ip_address):
        key = f"rate-limit:login:{ip_address}"
        cache.delete(key)
