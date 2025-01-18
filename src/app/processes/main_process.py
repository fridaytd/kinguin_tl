import random


from ..models.gsheet_model import Product
from .crwl import extract_offers_or_final_produce, extract_offers, get_state
from ..utils.logger import logger
from ..models.crwl_models import (
    CrwlOffer,
    FinalProduct,
    ExtractedOffer,
)
from ..utils.kinguin_client import kinguin_client
from ..shared.consts import CURRENCY
from ..models.api_models import PriceBase
from ..utils.price_utils import float_to_int_price, int_to_float_price
from ..utils.update_messages import (
    update_with_comparing_seller,
    update_with_min_price,
    no_need_update,
)
from ..models.api_models import Offer


def extract_offer_id_from_product_link(link: str) -> str:
    return link.split("/")[-1]


def update_offer(
    offer_id: str,
    price: PriceBase,
    declaredStock: int,
    min_quantity: int,
):
    kinguin_client.update_offer(
        offer_id=offer_id,
        price=price,
        declaredStock=declaredStock,
        min_quantity=min_quantity,
    )
    return


def calculate_priceiwtr_change_by_min_offer(
    product: Product,
    product_min_priceiwtr: float,
    product_max_priceiwtr: float | None,
    priceiwtr_of_min_offer: float,
) -> float:
    new_min_price_random = (
        priceiwtr_of_min_offer - product.DONGIAGIAM_MAX
        if priceiwtr_of_min_offer - product.DONGIAGIAM_MAX >= product_min_priceiwtr
        else product_min_priceiwtr
    )
    new_max_price_random = (
        priceiwtr_of_min_offer - product.DONGIAGIAM_MIN
        if priceiwtr_of_min_offer - product.DONGIAGIAM_MIN >= product_min_priceiwtr
        else product_min_priceiwtr
    )
    new_price_change = round(
        random.uniform(new_min_price_random, new_max_price_random),
        product.DONGIA_LAMTRON,
    )

    return new_price_change


def offers_compare_flow(
    product: Product,
    my_offer: Offer,
    offers: dict[str, CrwlOffer],
):
    valid_crwl_offers: dict[str, CrwlOffer] = {}

    # Get product data
    product_min_priceiwtr = product.min_price()
    product_max_priceiwtr = product.max_price()
    blacklist = product.blacklist()
    stock_without_unit = product.stock()

    # Convert price to comparatable price
    real_product_min_price = int_to_float_price(
        kinguin_client.from_priceiwtr_to_price(
            my_offer.productId,
            float_to_int_price(
                product_min_priceiwtr,
            ),
        )
    )
    real_product_max_price = (
        int_to_float_price(
            kinguin_client.from_priceiwtr_to_price(
                my_offer.productId,
                float_to_int_price(
                    product_max_priceiwtr,
                ),
            )
        )
        if product_max_priceiwtr
        else None
    )

    is_include_my_offer: bool = False

    min_price_offer: CrwlOffer | None = None

    # Filter valid offer and find min offer and find my offer if it valid
    for offer_id, offer in offers.items():
        real_offer_price = int_to_float_price(offer.price.amount)

        if my_offer.id == offer_id:
            is_include_my_offer = True

        if my_offer.id == offer_id or offer.seller.name not in blacklist:
            if (
                real_product_max_price
                and real_product_min_price <= real_offer_price <= real_product_max_price
            ) or (
                real_product_max_price is None
                and real_product_min_price <= real_offer_price
            ):
                valid_crwl_offers[offer_id] = offer
                if (
                    min_price_offer is None
                    or offer.price.amount < min_price_offer.price.amount
                ):
                    min_price_offer = offer

    if not is_include_my_offer:
        if min_price_offer is None:
            if product_max_priceiwtr:
                logger.info("Update by max price")
                target_priceiwtr = product_max_priceiwtr
                note_message, last_update_message = update_with_min_price(
                    price=target_priceiwtr,
                    stock=stock_without_unit,
                    min_quantity=product.MIN_UNIT_PER_ORDER,
                    unit_stock=product.UNIT_STOCK,
                    price_min=product_min_priceiwtr,
                    price_max=product_max_priceiwtr,
                )

            else:
                logger.info("Update by min price")
                target_priceiwtr = product_min_priceiwtr
                note_message, last_update_message = update_with_min_price(
                    price=target_priceiwtr,
                    stock=stock_without_unit,
                    unit_stock=product.UNIT_STOCK,
                    min_quantity=product.MIN_UNIT_PER_ORDER,
                    price_min=product_min_priceiwtr,
                    price_max=product_max_priceiwtr,
                )
        else:
            logger.info(f"Update price by price of {min_price_offer.seller.name}")
            priceiwtr_of_min_offer = int_to_float_price(
                kinguin_client.from_price_to_priceiwtr(
                    my_offer.productId,
                    min_price_offer.price.amount,
                )
            )
            new_price_change = calculate_priceiwtr_change_by_min_offer(
                product=product,
                product_min_priceiwtr=product_min_priceiwtr,
                product_max_priceiwtr=product_max_priceiwtr,
                priceiwtr_of_min_offer=priceiwtr_of_min_offer,
            )
            logger.info(new_price_change)
            target_priceiwtr = new_price_change
            note_message, last_update_message = update_with_comparing_seller(
                price=target_priceiwtr,
                stock=stock_without_unit,
                unit_stock=product.UNIT_STOCK,
                min_quantity=product.MIN_UNIT_PER_ORDER,
                price_min=product_min_priceiwtr,
                price_max=product_max_priceiwtr,
                comparing_price=priceiwtr_of_min_offer,
                comparing_seller=min_price_offer.seller.name,
            )

    else:
        if min_price_offer:
            if min_price_offer.id == my_offer.id:
                target_priceiwtr = None
                logger.info("Do not need to update")
                note_message, last_update_message = no_need_update(
                    my_seller=min_price_offer.seller.name,
                    price=my_offer.priceIWTR.amount,
                    stock=my_offer.declaredStock // product.UNIT_STOCK,
                    min_quantity=product.MIN_UNIT_PER_ORDER,
                    unit_stock=product.UNIT_STOCK,
                    price_min=product_min_priceiwtr,
                    price_max=product_max_priceiwtr,
                )

            else:
                logger.info(f"Update price by price of {min_price_offer.seller.name}")
                priceiwtr_of_min_offer = int_to_float_price(
                    kinguin_client.from_price_to_priceiwtr(
                        my_offer.productId,
                        min_price_offer.price.amount,
                    )
                )
                new_price_change = calculate_priceiwtr_change_by_min_offer(
                    product=product,
                    product_min_priceiwtr=product_min_priceiwtr,
                    product_max_priceiwtr=product_max_priceiwtr,
                    priceiwtr_of_min_offer=priceiwtr_of_min_offer,
                )
                logger.info(new_price_change)
                target_priceiwtr = new_price_change
                note_message, last_update_message = update_with_comparing_seller(
                    price=target_priceiwtr,
                    stock=stock_without_unit,
                    unit_stock=product.UNIT_STOCK,
                    min_quantity=product.MIN_UNIT_PER_ORDER,
                    price_min=product_min_priceiwtr,
                    price_max=product_max_priceiwtr,
                    comparing_price=priceiwtr_of_min_offer,
                    comparing_seller=min_price_offer.seller.name,
                )

        else:
            if product_max_priceiwtr:
                logger.info("Update by max price")
                target_priceiwtr = product_max_priceiwtr
                note_message, last_update_message = update_with_min_price(
                    price=target_priceiwtr,
                    stock=stock_without_unit,
                    min_quantity=product.MIN_UNIT_PER_ORDER,
                    unit_stock=product.UNIT_STOCK,
                    price_min=product_min_priceiwtr,
                    price_max=product_max_priceiwtr,
                )

            else:
                logger.info("Update by min price")
                target_priceiwtr = product_min_priceiwtr
                note_message, last_update_message = update_with_min_price(
                    price=target_priceiwtr,
                    stock=stock_without_unit,
                    min_quantity=product.MIN_UNIT_PER_ORDER,
                    unit_stock=product.UNIT_STOCK,
                    price_min=product_min_priceiwtr,
                    price_max=product_max_priceiwtr,
                )

    if target_priceiwtr:
        update_offer(
            offer_id=my_offer.id,
            price=PriceBase(
                amount=float_to_int_price(target_priceiwtr),
                currency=CURRENCY,
            ),
            declaredStock=stock_without_unit * product.UNIT_STOCK,
            min_quantity=product.MIN_UNIT_PER_ORDER,
        )
    product.Note = note_message
    product.Last_update = last_update_message
    product.update()


def ingame_category_compare_flow(
    sb,
    product: Product,
    my_offer: Offer,
    final_products: dict[str, FinalProduct],
):
    product_min_priceiwtr = product.min_price()
    product_max_priceiwtr = product.max_price()
    # blacklist = product.blacklist()
    # stock = product.stock()

    # Convert price to comparatable price
    real_product_min_price = int_to_float_price(
        kinguin_client.from_priceiwtr_to_price(
            my_offer.productId,
            float_to_int_price(
                product_min_priceiwtr,
            ),
        )
    )
    real_product_max_price = (
        int_to_float_price(
            kinguin_client.from_priceiwtr_to_price(
                my_offer.productId,
                float_to_int_price(
                    product_max_priceiwtr,
                ),
            )
        )
        if product_max_priceiwtr
        else None
    )

    valid_final_products: dict[str, FinalProduct] = {}

    for product_id, final_product in final_products.items():
        real_offer_price = int_to_float_price(final_product.price.calculated)
        if (
            product_max_priceiwtr
            and product_min_priceiwtr <= real_offer_price <= product_max_priceiwtr
        ) or (
            product_max_priceiwtr is None and product_min_priceiwtr <= real_offer_price
        ):
            valid_final_products[product_id] = final_product

    offers: dict[str, CrwlOffer] = {}
    for product_id, final_product in valid_final_products.items():
        state = get_state(
            sb,
            f"https://www.kinguin.net/category/{final_product.externalId}/{final_product.attributes.urlKey}",
        )
        offers.update(extract_offers(state))

    offers_compare_flow(
        product=product,
        my_offer=my_offer,
        offers=offers,
    )


def check_product_compare_flow(
    sb,
    product: Product,
):
    logger.info(f"Processing for {product.Product_name}")
    logger.info(f"Crawling at: {product.PRODUCT_COMPARE}")

    my_offer_id = extract_offer_id_from_product_link(product.Product_link)

    my_offer = kinguin_client.get_offer(offer_id=my_offer_id)

    extracted_data = extract_offers_or_final_produce(sb, product.PRODUCT_COMPARE)

    if isinstance(extracted_data, ExtractedOffer):
        offers_compare_flow(
            product=product, my_offer=my_offer, offers=extracted_data.data
        )

    else:
        ingame_category_compare_flow(
            sb,
            product=product,
            my_offer=my_offer,
            final_products=extracted_data.data,
        )


def no_check_product_compare_flow(
    product: Product,
):
    product_min_price = product.min_price()
    product_max_price = product.max_price()
    stock = product.stock()

    real_stock = stock * product.UNIT_STOCK

    int_price = float_to_int_price(product_min_price)

    my_offer_id = extract_offer_id_from_product_link(product.Product_link)

    update_offer(
        offer_id=my_offer_id,
        declaredStock=real_stock,
        price=PriceBase(amount=int_price, currency=CURRENCY),
        min_quantity=product.MIN_UNIT_PER_ORDER,
    )

    note_message, last_update_message = update_with_min_price(
        price=product_min_price,
        stock=stock,
        min_quantity=product.MIN_UNIT_PER_ORDER,
        unit_stock=product.UNIT_STOCK,
        price_min=product_min_price,
        price_max=product_max_price,
    )

    product.Note = note_message
    product.Last_update = last_update_message
    product.update()


def process(
    sb,
    product: Product,
):
    if product.CHECK_PRODUCT_COMPARE == 1:
        logger.info("Must compare product")
        check_product_compare_flow(sb, product)
    else:
        no_check_product_compare_flow(product)
