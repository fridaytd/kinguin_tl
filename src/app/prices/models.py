from pydantic import BaseModel

from app.shared.consts import API_VS_REAL_PRICE_CONVERT_RATE
from app.kinguin.models import CommissionRule


class PriceBase(BaseModel):
    pass


class APIPrice(PriceBase):
    amount: int

    def to_real_price(
        self,
    ) -> "RealPrice":
        real_price: float = float(self.amount) / API_VS_REAL_PRICE_CONVERT_RATE
        return RealPrice(amount=real_price)


class RealPrice(PriceBase):
    amount: float

    def to_api_price(self) -> APIPrice:
        api_price = int(self.amount * API_VS_REAL_PRICE_CONVERT_RATE)
        return APIPrice(amount=api_price)


class PriceCustomerPay(APIPrice):
    def to_priceiwtr(
        self,
        commission_rule: CommissionRule,
    ) -> "PriceIWTR":
        priceiwtr = int(
            round(
                (self.amount - commission_rule.fixedAmount)
                * 100
                / (100 + commission_rule.percentValue),
                0,
            )
        )
        return PriceIWTR(amount=priceiwtr)


class PriceIWTR(APIPrice):
    def to_price_customer_pay(
        self,
        commission_rule: CommissionRule,
    ) -> PriceCustomerPay:
        price_customer_pay = int(
            round(
                self.amount * (100 + commission_rule.percentValue) / 100
                + commission_rule.fixedAmount,
                0,
            )
        )
        return PriceCustomerPay(amount=price_customer_pay)


class UnitPriceBase(PriceBase):
    amount: int | float


class APIUnitPrice(UnitPriceBase):
    def to_real_unit_price(
        self,
    ) -> "RealUnitPrice":
        if isinstance(self.amount, int):
            real_unit_price: float = float(self.amount) / API_VS_REAL_PRICE_CONVERT_RATE
        else:
            real_unit_price: float = self.amount / API_VS_REAL_PRICE_CONVERT_RATE

        return RealUnitPrice(amount=real_unit_price)

    def to_price_customer_pay(
        self,
        min_quantity_per_order: int,
    ) -> PriceCustomerPay:
        price_customer_pay: int = int(self.amount * min_quantity_per_order)

        return PriceCustomerPay(amount=price_customer_pay)


class RealUnitPrice(UnitPriceBase):
    def to_api_unit_price(
        self,
    ) -> APIUnitPrice:
        api_unit_price: float = self.amount * API_VS_REAL_PRICE_CONVERT_RATE

        return APIUnitPrice(amount=api_unit_price)

    def to_unit_price_per_unit_stock(
        self,
        unit_stock: int,
    ) -> "RealUnitPricePerUnitStock":
        unit_price_per_unit_stock: float = self.amount * unit_stock
        return RealUnitPricePerUnitStock(
            amount=unit_price_per_unit_stock, unit_stock=unit_stock
        )


class RealUnitPricePerUnitStock(UnitPriceBase):
    unit_stock: int

    def to_real_unit_price(
        self,
    ) -> RealUnitPrice:
        real_unit_price: float = float(self.amount) / self.unit_stock
        return RealUnitPrice(amount=real_unit_price)

    def to_api_unit_price(
        self,
    ) -> APIUnitPrice:
        real_unit_price = self.to_real_unit_price()
        return real_unit_price.to_api_unit_price()


class APIUnitPricePerUnitStock(UnitPriceBase):
    unit_stock: int

    def to_real_unit_price_per_unit_stock(
        self,
    ) -> RealUnitPricePerUnitStock:
        real_unit_price_per_unit_stock: float = (
            float(self.amount) / API_VS_REAL_PRICE_CONVERT_RATE
        )
        return RealUnitPricePerUnitStock(
            amount=real_unit_price_per_unit_stock, unit_stock=self.unit_stock
        )
