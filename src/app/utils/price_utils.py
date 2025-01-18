from ..shared.consts import PRICE_CONVERT_RATE


def float_to_int_price(
    price: float,
) -> int:
    return int(price * PRICE_CONVERT_RATE)


def int_to_float_price(
    price: int,
) -> float:
    return float(price) / PRICE_CONVERT_RATE
