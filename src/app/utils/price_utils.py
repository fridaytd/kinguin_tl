from ..shared.consts import PRICE_CONVERT_RATE
from ..models.api_models import CommissionRule


def float_to_int_price(
    price: float,
) -> int:
    return int(price * PRICE_CONVERT_RATE)


def int_to_float_price(
    price: int,
) -> float:
    return float(price) / PRICE_CONVERT_RATE


def priceiwtr_to_price(
    priceiwtr: int,
    commission_rule: CommissionRule,
) -> int:
    return int(
        round(
            priceiwtr * (100 + commission_rule.percentValue) / 100
            + commission_rule.fixedAmount,
            0,
        )
    )


def price_to_priceiwtr(
    price: int,
    commission_rule: CommissionRule,
):
    return int(
        round(
            (price - commission_rule.fixedAmount)
            * 100
            / (100 + commission_rule.percentValue),
            0,
        )
    )
