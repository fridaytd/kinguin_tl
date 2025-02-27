from datetime import datetime


def last_update_message(
    now: datetime,
) -> str:
    formatted_date = now.strftime("%d/%m/%Y %H:%M:%S")
    return formatted_date


def update_with_min_price(
    price: float,
    priceiwtr: float,
    unit_price: int | float,
    stock: int,
    unit_stock: int,
    min_quantity: int | None,
    price_min: float,
    price_max: float | None = None,
) -> tuple[str, str]:
    now = datetime.now()
    _last_update_message = last_update_message(now)
    note_message = f"""{_last_update_message}:Giá đã cập nhật thành công; PriceCustomerPay: {price} ;PriceIWTR = {priceiwtr}; Unit Price: {unit_price}; Stock = {stock}; Unit Stock = {unit_stock}; MinUnitPerOrder = {min_quantity}; UnitPriceMin = {price_min}, UnitPriceMax = {price_max}"""
    return note_message, _last_update_message


def update_with_comparing_seller(
    price: float,
    priceiwtr: float,
    unit_price: int | float,
    stock: int,
    unit_stock: int,
    price_min: float,
    min_quantity: int | None,
    comparing_seller: str,
    comparing_seller_actual_price: float,
    comparing_seller_unit_price: float | int,
    price_max: float | None = None,
) -> tuple[str, str]:
    now = datetime.now()
    _last_update_message = last_update_message(now)
    note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; PriceCustomerPay: {price}; PriceIWTR = {priceiwtr}; Unit Price: {unit_price}; Stock = {stock}; Unit Stock = {unit_stock}; MinUnitPerOrder = {min_quantity}; UnitPriceMin = {price_min}, UnitPriceMax = {price_max} - Seller: {comparing_seller}, SellerPriceIWTR: {comparing_seller_actual_price}, SellerUnitPrice: {comparing_seller_unit_price}"""
    return note_message, _last_update_message


# def no_need_update(
#     my_seller: str,
#     price: float,
#     stock: int,
#     min_quantity: int | None,
#     unit_stock: int,
#     price_min: float,
#     price_max: float | None = None,
# ) -> tuple[str, str]:
#     now = datetime.now()
#     _last_update_message = last_update_message(now)
#     note_message = f"{last_update_message(now)}: Không cần cập nhật giá vì {my_seller} Đã có giá nhỏ nhất: Price = {price}; Stock = {stock}; Unit Stock = {unit_stock}; MinUnitPerOrder = {min_quantity}; Pricemin = {price_min}, Pricemax = {price_max}."
#     return note_message, _last_update_message
