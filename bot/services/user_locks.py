"""
Блокировки для синхронизации операций с балансом пользователей.

Используется для предотвращения race conditions при операциях с балансом.
"""
import asyncio
from collections import defaultdict


user_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
