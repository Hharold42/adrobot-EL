"""Общие зависимости FastAPI."""

from collections.abc import AsyncGenerator

from fastapi import Request

from .keitaro import KeitaroClient


async def get_keitaro(request: Request) -> AsyncGenerator[KeitaroClient, None]:
    """Выдаёт KeitaroClient на время запроса.

    Ключ API: заголовок X-Keitaro-Key от фронта, иначе ключ из .env.
    """
    api_key = request.headers.get("x-keitaro-key") or None
    client = KeitaroClient(api_key=api_key)
    try:
        yield client
    finally:
        await client.close()
