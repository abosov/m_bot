import base64
import uuid

import httpx

import config


class YooKassaClientError(Exception):
    pass


class YooKassaClient:
    def __init__(self) -> None:
        self.shop_id = (config.YOOKASSA_SHOP_ID or "").strip()
        self.secret_key = (config.YOOKASSA_SECRET_KEY or "").strip()
        self.base_url = "https://api.yookassa.ru/v3"

    def is_enabled(self) -> bool:
        return bool(self.shop_id and self.secret_key)

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{self.shop_id}:{self.secret_key}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    async def create_payment(self, *, amount_rub_int: int, description: str, return_url: str) -> dict:
        if not self.is_enabled():
            raise YooKassaClientError("YooKassa credentials are not configured")

        idem_key = str(uuid.uuid4())
        payload = {
            "amount": {"value": f"{amount_rub_int:.2f}", "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": description,
        }

        headers = {
            "Authorization": self._auth_header(),
            "Idempotence-Key": idem_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self.base_url}/payments", json=payload, headers=headers)

        if response.status_code >= 400:
            raise YooKassaClientError(f"YooKassa API error: status={response.status_code}")

        data = response.json()
        if not isinstance(data, dict) or not data.get("id"):
            raise YooKassaClientError("Invalid YooKassa response")
        return data
