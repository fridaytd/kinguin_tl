import os

from datetime import datetime
import requests
from requests.exceptions import HTTPError

from ..shared.consts import KINGUIN_TOKEN_BASE_URL, KINGUIN_API_BASE_URL
from .logger import logger
from ..models.api_models import Offer, PriceBase


class Token:
    def __init__(
        self,
    ) -> None:
        # Init access token
        res = requests.post(
            KINGUIN_TOKEN_BASE_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "client_id": os.environ["KINGUIN_CLIENT_ID"],
                "client_secret": os.environ["KINGUIN_SECRET_KEY"],
            },
        )

        res.raise_for_status()

        res_payload: dict = res.json()

        self.access_token: str = res_payload["access_token"]
        self.expires_in: int = res_payload["expires_in"]

        current_timestamp: float = datetime.now().timestamp()

        self.timestamp_expires: float = current_timestamp + self.expires_in - 5

    def is_expired(
        self,
    ) -> bool:
        current_timestamp: float = datetime.now().timestamp()
        return current_timestamp > self.timestamp_expires

    def refresh_token(
        self,
    ) -> None:
        res = requests.post(
            KINGUIN_TOKEN_BASE_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "client_id": os.environ["KINGUIN_CLIENT_ID"],
                "client_secret": os.environ["KINGUIN_SECRET_KEY"],
            },
        )

        res.raise_for_status()

        res_payload: dict = res.json()

        self.access_token = res_payload["access_token"]
        self.expires_in = res_payload["expires_in"]

        current_timestamp = datetime.now().timestamp()

        self.timestamp_expires = current_timestamp + self.expires_in - 5

    def ensure_valid_token(
        self,
    ) -> None:
        if self.is_expired():
            logger.info("Refresh token")
            self.refresh_token()
            return

        logger.info("Valid token")


class KinguinClient:
    def __init__(
        self,
    ):
        self.token: Token = Token()

    def get_offer(
        self,
        offer_id: str,
    ):
        self.token.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json",
        }

        res = requests.get(
            f"{KINGUIN_API_BASE_URL}/api/v1/offers/{offer_id}", headers=headers
        )
        res.raise_for_status()

        return Offer.model_validate(res.json())

    def get_offers(
        self,
    ):
        self.token.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json",
        }

        res = requests.get(f"{KINGUIN_API_BASE_URL}/api/v1/offers", headers=headers)
        res.raise_for_status()

        return res.json()

    def update_offer(
        self,
        offer_id: str,
        price: PriceBase,
        declaredStock: int,
        min_quantity: int | None,
    ) -> None:
        self.token.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "price": price.model_dump(mode="json"),
            "declaredStock": declaredStock,
        }

        if min_quantity:
            payload["minQuantity"] = min_quantity

        res = requests.patch(
            f"{KINGUIN_API_BASE_URL}/api/v1/offers/{offer_id}",
            headers=headers,
            json=payload,
        )
        try:
            res.raise_for_status()

        except HTTPError:
            logger.error(res.text)
            res.raise_for_status()

    def from_priceiwtr_to_price(
        self,
        kpc_product_id: str,
        priceiwtr: int,
    ) -> int:
        self.token.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "kpcProductId": kpc_product_id,
            "priceIWTR": priceiwtr,
        }

        res = requests.get(
            f"{KINGUIN_API_BASE_URL}/api/v1/offers/calculations/priceAndCommission",
            headers=headers,
            params=payload,
        )
        try:
            res.raise_for_status()

        except HTTPError:
            logger.error(res.text)
            res.raise_for_status()

        return res.json()["price"]

    def from_price_to_priceiwtr(
        self,
        kpc_product_id: str,
        price: int,
    ) -> int:
        self.token.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "kpcProductId": kpc_product_id,
            "price": price,
        }

        res = requests.get(
            f"{KINGUIN_API_BASE_URL}/api/v1/offers/calculations/priceAndCommission",
            headers=headers,
            params=payload,
        )
        try:
            res.raise_for_status()

        except HTTPError:
            logger.error(res.text)
            res.raise_for_status()

        return res.json()["priceIWTR"]


kinguin_client = KinguinClient()
