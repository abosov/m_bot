import base64
from decimal import Decimal
import uuid

import httpx

import config


class YooKassaClientError(Exception):
    pass


class YooKassaClientResponseError(YooKassaClientError):
    def __init__(self, status_code: int, message: str = "YooKassa API error") -> None:
        super().__init__(f"{message}: status={status_code}")
        self.status_code = status_code


class YooKassaClientNetworkError(YooKassaClientError):
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

    @staticmethod
    def _format_amount_value(amount_minor: int) -> str:
        return format((Decimal(amount_minor) / Decimal("100")).quantize(Decimal("0.01")), "f")

    async def create_payment(
        self,
        *,
        amount_minor: int | None = None,
        amount_rub_int: int | None = None,
        currency: str = "RUB",
        description: str,
        return_url: str,
        idempotence_key: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        if not self.is_enabled():
            raise YooKassaClientError("YooKassa credentials are not configured")
        if amount_minor is None:
            if amount_rub_int is None:
                raise YooKassaClientError("Payment amount is required")
            amount_minor = amount_rub_int * 100

        idem_key = idempotence_key or str(uuid.uuid4())
        payload = {
            "amount": {"value": self._format_amount_value(amount_minor), "currency": currency},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": description,
        }
        if metadata:
            payload["metadata"] = metadata

        headers = {
            "Authorization": self._auth_header(),
            "Idempotence-Key": idem_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(f"{self.base_url}/payments", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise YooKassaClientNetworkError("YooKassa request failed") from exc

        if response.status_code >= 400:
            raise YooKassaClientResponseError(response.status_code)

        data = response.json()
        if not isinstance(data, dict) or not data.get("id"):
            raise YooKassaClientError("Invalid YooKassa response")
        return data
