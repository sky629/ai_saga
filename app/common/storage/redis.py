import asyncio
import os
from collections import namedtuple
from enum import IntEnum
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple, Union

import rapidjson
import redis

from app.common.exception import ServerError
from app.common.logging import logger
from app.common.utils.singleton import Singleton
from config.settings import settings


class CacheExpire(IntEnum):
    SECOND = 1
    MINUTE = 60
    HOUR = 60 * 60
    DAY = 60 * 60 * 24
    WEEK = 60 * 60 * 24 * 7
    MONTH = 60 * 60 * 24 * 30


def aioredis_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis.exceptions.RedisError as e:

            logger.exception("Failed to execute a aioredis function.")
            raise ServerError from e
        except Exception as e:
            logger.critical(
                "Failed to execute a aioredis function. Occurred unknown error",
                exc_info=1,
            )
            raise ServerError from e

    return wrapper


ConnectionInfo = namedtuple("ConnectionInfo", ("hosts", "db", "minsize", "maxsize"))


_POOLS: Dict[str, redis] = {}


class _RedisStorage(metaclass=Singleton):
    def get_connection_info(self, alias: str = "default") -> ConnectionInfo:
        # Use settings from config instead of config.redis
        redis_url = settings.redis_url
        # Extract host:port from redis_url (format: redis://host:port)
        if redis_url.startswith("redis://"):
            hosts = redis_url.replace("redis://", "")
        else:
            hosts = redis_url or "localhost:6379"

        db = os.environ.get(f"REDIS_{alias.upper()}_DB") or 1
        minsize = os.environ.get(f"REDIS_{alias.upper()}_MINSIZE") or 1
        maxsize = os.environ.get(f"REDIS_{alias.upper()}_MAXSIZE") or 10
        return ConnectionInfo(
            hosts=hosts, db=int(db), minsize=int(minsize), maxsize=int(maxsize)
        )

    async def get_connection(
        self,
        alias: str = "default",
        encoding: str = "utf8",
        decode_responses=True,
    ) -> redis:
        """https://aioredis.readthedocs.io/en/v1.3.0/api_reference.html#aioredis.create_redis_pool"""
        key = f"{alias}:{encoding}:{int(decode_responses)}"
        if key not in _POOLS:
            conn_info = self.get_connection_info(alias)
            logger.info("Connecting to Redis: %s", conn_info.hosts)
            options = {
                "encoding": encoding,
                "decode_responses": decode_responses,
            }
            _redis = await redis.asyncio.from_url(
                f"redis://{conn_info.hosts}",
                db=conn_info.db,
                **options,
            )
            _POOLS[key] = _redis
        return _POOLS[key]

    async def close_all(self):
        logger.info("Shutting down all Redis connection pools...")
        global _POOLS
        f = []
        for _, v in _POOLS.items():
            f.append(v.close())
        _ = await asyncio.gather(*f)
        _POOLS = {}
        logger.info("Successfully shut down all Redis connection pools.")


class _CacheClient:
    _alias: str = "default"
    _ttl: Union[int, CacheExpire] = CacheExpire.SECOND * 1  # 1 second

    def _get_key(self, *args, **kwargs):
        raise NotImplementedError

    @aioredis_error_handler
    async def get_connection(self):
        conn = await pools.get_connection(alias=self._alias)
        return conn

    @aioredis_error_handler
    async def get(self, *args, **kwargs) -> Optional[Any]:
        conn = await self.get_connection()
        result: Optional[str] = await conn.get(self._get_key(*args, **kwargs))
        return rapidjson.loads(result) if isinstance(result, str) else result

    @aioredis_error_handler
    async def mget(
        self,
        key_sources: List[Union[str, tuple]],
    ) -> List[Optional[Any]]:
        if not key_sources:
            return []
        keys = [
            (
                self._get_key(*key_source)
                if isinstance(key_source, tuple)
                else self._get_key(key_source)
            )
            for key_source in key_sources
        ]
        conn = await self.get_connection()
        results: List[Optional[str]] = await conn.mget(*keys)
        return [
            rapidjson.loads(result) if isinstance(result, str) else result
            for result in results
        ]

    @aioredis_error_handler
    async def delete(self, *args, **kwargs):
        conn = await self.get_connection()
        await conn.delete(self._get_key(*args, **kwargs))

    @aioredis_error_handler
    async def batch_delete(self, keys):
        if keys:
            task = [self.delete(key) for key in keys]
            await asyncio.gather(*task)

    @aioredis_error_handler
    async def set(
        self,
        *args,
        value: Optional[Union[str, dict, List[dict]]] = None,
        expire: Optional[Union[int, CacheExpire]] = None,
    ):
        serialized_value: str = rapidjson.dumps(value)
        conn = await self.get_connection()
        await conn.set(
            self._get_key(*args),
            value=serialized_value,
            ex=int(expire if expire is not None else self._ttl),
        )

    @aioredis_error_handler
    async def set_using_pipeline(
        self,
        key_with_value_list: List[Tuple[str, Any]],
        expire: Optional[Union[int, CacheExpire]] = None,
    ):
        conn = await self.get_connection()
        pipe = conn.pipeline()
        for key, value in key_with_value_list:
            serialized_value: str = rapidjson.dumps(value)
            pipe.set(
                self._get_key(key),
                value=serialized_value,
                ex=int(expire if expire is not None else self._ttl),
            )
        await pipe.execute()


pools = _RedisStorage()
