import json
import hashlib
import time

try:
    import redis
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False


class CacheService:
    def __init__(self):
        self.use_redis = False
        self.local_cache = {}

        if REDIS_AVAILABLE:
            try:
                self.client = redis.Redis(
                    host="localhost",
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=1
                )
                self.client.ping()
                self.use_redis = True
            except Exception:
                self.use_redis = False

    def _now(self):
        return int(time.time())

    def _is_expired(self, expiry):
        return expiry is not None and self._now() > expiry

    def get(self, key: str):
        if self.use_redis:
            try:
                val = self.client.get(key)
                return json.loads(val) if val else None
            except Exception:
                return None
        else:
            item = self.local_cache.get(key)
            if not item:
                return None

            value, expiry = item
            if self._is_expired(expiry):
                del self.local_cache[key]
                return None

            return value

    def set(self, key: str, value, ttl=300):
        if self.use_redis:
            try:
                self.client.setex(key, ttl, json.dumps(value))
            except Exception:
                pass
        else:
            expiry = self._now() + ttl if ttl else None
            self.local_cache[key] = (value, expiry)
