from pydantic import BaseModel


class OfferPrice(BaseModel):
    amount: int
    currency: str


class Seller(BaseModel):
    id: int
    name: str


class CrwlOffer(BaseModel):
    id: str
    productId: str
    price: OfferPrice
    seller: Seller


class FinalProductPrice(BaseModel):
    calculated: int
    lowestOffer: int


class FinalProductAttribute(BaseModel):
    urlKey: str


class FinalProduct(BaseModel):
    id: str
    offerId: str
    externalId: str
    price: FinalProductPrice
    attributes: FinalProductAttribute
