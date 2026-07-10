import logging
import valkey
import msgpack

from typing import Any, List, Iterator

from utils.cache import CacheManager, Cache

default_config = {"db": 0, "host": "valkey", "port": 6379, "tag": "data"}


class Batcher:
    def __init__(self, iterable, n=1):
        self.iterable = iterable
        self.n = n

    def __iter__(self):
        l = len(self.iterable)
        for ndx in range(0, l, self.n):
            yield self.iterable[ndx : min(ndx + self.n, l)]


@CacheManager.export("valkey")
class ValkeyCache(Cache, config=default_config, version="0.1"):
    def __init__(self, config=None):
        super().__init__(config)
        # NOTE: previous call 'redis.Redis(...)'
        self.r = valkey.Valkey(
            host=self.config.get("host"),
            port=self.config.get("port"),
            db=self.config.get("db"),
        )

    def set(self, id: str, data: Any) -> bool:
        try:
            packed = msgpack.packb(data, use_bin_type=True)
            tag = self.config.get("tag")
            self.r.set(f"{tag}:{id}", packed)
            return True
        except Exception as e:
            logging.error(f"valKeyCache {e}")
            return False

    def get(self, id: str) -> Any:
        try:
            tag = self.config.get("tag")
            packed = self.r.get(f"{tag}:{id}")
            if packed is None:
                return None
            return msgpack.unpackb(packed, raw=False)
        except Exception as e:
            logging.error(f"valKeyCache {e}")
            return None

    def __iter__(self) -> Iterator:
        try:
            tag = self.config.get("tag")
            start = len(f"{tag}:")
            keys = list(self.r.scan_iter(f"{tag}:*", count=500))
            while keys:
                batch_keys = keys[:500]
                keys = keys[500:]
                values = self.r.mget(batch_keys)
                for k, v in zip(batch_keys, values):
                    if v is None:
                        continue
                    yield k[start:].decode("utf-8"), msgpack.unpackb(v, raw=False)
        except Exception as e:
            logging.error(f"valKeyCache {e}")
            yield from []

    def delete(self, data_id: str) -> bool:
        try:
            tag = self.config.get("tag")
            return self.r.delete(f"{tag}:{id}")
        except Exception as e:
            logging.error(f"valKeyCache {e}")
            return None

    def delete_by_value_field(self, field: str, target: Any) -> int:
        try:
            tag = self.config.get("tag")
            deleted = 0
            batch = []

            for raw_key in self.r.scan_iter(f"{tag}:*", count=500):
                packed = self.r.get(raw_key)
                if packed is None:
                    continue

                value = msgpack.unpackb(packed, raw=False)
                if isinstance(value, dict) and value.get(field) == target:
                    batch.append(raw_key)

                if len(batch) >= 500:
                    deleted += self.r.delete(*batch)
                    batch = []

            if batch:
                deleted += self.r.delete(*batch)

            return deleted
        except Exception as e:
            logging.error(f"valKeyCache {e}")
            return 0

    def keys(self) -> List[str]:
        try:
            tag = self.config.get("tag")
            start = len(f"{tag}:")
            keys = self.r.scan_iter(f"{tag}:*", 500)

            # print([x for x in Batcher(keys, 2)])
            return [key[start:].decode("utf-8") for key in keys]
        except Exception as e:
            logging.error(f"valKeyCache {e}")
            return []


