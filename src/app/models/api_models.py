from pydantic import BaseModel


class PriceBase(BaseModel):
    amount: int
    currency: str


# class PriceIWTR(PriceBase):
#     pass


# class Price(PriceBase):
#     pass


class Offer(BaseModel):
    id: str
    productId: str
    name: str
    sellerId: int
    status: str
    block: str | None = None
    priceIWTR: PriceBase
    price: PriceBase
    declaredStock: int
    minQuantity: int | None = None
