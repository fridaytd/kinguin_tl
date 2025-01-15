import os
import random

from datetime import datetime

from ..models.gsheet_model import Product
from .crwl import get_state, extract_ingame_category, extract_offers
from ..utils.logger import logger
from ..models.crwl_models import CrwlOffer, OfferPrice, FinalProduct
from ..utils.kinguin_client import kinguin_client
from ..shared.consts import CURRENCY


def last_update_message(
    now: datetime,
) -> str:
    formatted_date = now.strftime("%d/%m/%Y %H:%M:%S")
    return formatted_date


def extract_offer_id_from_product_link(link: str) -> str:
    return link.split("/")[-1]


def update_by_price_and_stock(
    offer_id: str,
    target_price: float,
    stock: int,
    product_id: str | None = None,
):
    fake_price: int = int(target_price * 100)
    if product_id:
        price_iwtr = kinguin_client.calculate_merchant_commission_infomation(
            kpc_product_id=product_id, price=fake_price
        )["priceIWTR"]
        logger.info(f"UPdate price: {price_iwtr}")

    else:
        product_id_: str = kinguin_client.get_offer(offer_id=offer_id)["productId"]
        price_iwtr: int = kinguin_client.calculate_merchant_commission_infomation(
            kpc_product_id=product_id_, price=fake_price
        )["priceIWTR"]
        logger.info(f"Update price: {price_iwtr}")

    kinguin_client.update_offer(
        offer_id=offer_id,
        price=OfferPrice(
            amount=price_iwtr,
            currency=CURRENCY,
        ),
        declaredStock=stock,
    )


def calculate_price_change_by_min_offer(
    product: Product,
    product_min_price: float,
    product_max_price: float | None,
    min_price_offer: CrwlOffer,
) -> float:
    real_min_price: float = float(min_price_offer.price.amount) / 100
    new_min_price_random = (
        real_min_price - product.DONGIAGIAM_MAX
        if real_min_price - product.DONGIAGIAM_MAX >= product_min_price
        else product_min_price
    )
    new_max_price_random = (
        real_min_price - product.DONGIAGIAM_MIN
        if real_min_price - product.DONGIAGIAM_MIN >= product_min_price
        else product_min_price
    )
    new_price_change = round(
        random.uniform(new_min_price_random, new_max_price_random),
        product.DONGIA_LAMTRON,
    )

    return new_price_change


def offers_compare_flow(
    product: Product,
    offers: dict[str, CrwlOffer],
):
    valid_offers: dict[str, CrwlOffer] = {}
    my_offer: CrwlOffer | None = None

    product_min_price = product.min_price()
    product_max_price = product.max_price()
    blacklist = product.blacklist()
    stock = product.stock()

    my_offer_id: str = extract_offer_id_from_product_link(product.Product_link)

    min_price_offer: CrwlOffer | None = None

    # Filter valid offer and find min offer and find my offer if it valid
    for offer_id, offer in offers.items():
        real_offer_price: float = float(offer.price.amount) / 100

        if my_offer_id == offer_id or offer.seller.name not in blacklist:
            if (
                product_max_price
                and product_min_price <= real_offer_price <= product_max_price
            ) or (product_max_price is None and product_min_price <= real_offer_price):
                valid_offers[offer_id] = offer
                if (
                    min_price_offer is None
                    or offer.price.amount < min_price_offer.price.amount
                ):
                    min_price_offer = offer

                if my_offer_id == offer_id:
                    my_offer = offer

    now = datetime.now()

    if my_offer is None:
        if min_price_offer is None:
            if product_max_price:
                logger.info("Update by max price")
                target_price = product_max_price
                note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {target_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}"""

            else:
                logger.info("Update by min price")
                target_price = product_min_price
                note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {target_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}"""

        else:
            logger.info(f"Update price by price of {min_price_offer.seller.name}")
            new_price_change = calculate_price_change_by_min_offer(
                product=product,
                product_min_price=product_min_price,
                product_max_price=product_max_price,
                min_price_offer=min_price_offer,
            )
            logger.info(new_price_change)
            target_price = new_price_change
            note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {target_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}, , GiaSosanh = {float(min_price_offer.price.amount) / 100} - Seller: {min_price_offer.seller.name}."""

    else:
        if min_price_offer:
            if min_price_offer.id == my_offer.id:
                target_price = None
                logger.info("Do not need to update")
                note_message_var = f"{last_update_message(now)}: Không cần cập nhật giá vì {os.environ['MY_SELLER_NAME']} Đã có giá nhỏ nhất: Price = {float(min_price_offer.price.amount) / 100}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}."

            else:
                logger.info(f"Update price by price of {min_price_offer.seller.name}")

                new_price_change = calculate_price_change_by_min_offer(
                    product=product,
                    product_min_price=product_min_price,
                    product_max_price=product_max_price,
                    min_price_offer=min_price_offer,
                )
                logger.info(new_price_change)
                target_price = new_price_change
                note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {target_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}, , GiaSosanh = {float(min_price_offer.price.amount) / 100} - Seller: {min_price_offer.seller.name}"""

        else:
            if product_max_price:
                logger.info("Update by max price")
                target_price = product_max_price
                note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {target_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}"""

            else:
                logger.info("Update by min price")
                target_price = product_min_price
                note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {target_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}"""

    if min_price_offer:
        product_id = min_price_offer.productId

    else:
        product_id = None

    if target_price:
        update_by_price_and_stock(
            offer_id=my_offer_id,
            target_price=target_price,
            stock=stock,
            product_id=product_id,
        )
    product.Note = note_message
    product.Last_update = last_update_message(now)

    product.update()


def ingame_category_compare_flow(
    sb,
    product: Product,
    final_products: dict[str, FinalProduct],
):
    product_min_price = product.min_price()
    product_max_price = product.max_price()
    # blacklist = product.blacklist()
    # stock = product.stock()

    my_offer_id = extract_offer_id_from_product_link(product.Product_link)

    valid_final_products: dict[str, FinalProduct] = {}

    for product_id, final_product in final_products.items():
        real_offer_price: float = float(final_product.price.calculated) / 100
        if (
            product_max_price
            and product_min_price <= real_offer_price <= product_max_price
        ) or (product_max_price is None and product_min_price <= real_offer_price):
            valid_final_products[product_id] = final_product

    offers: dict[str, CrwlOffer] = {}
    for product_id, final_product in valid_final_products.items():
        state = get_state(
            sb,
            f"https://www.kinguin.net/category/{final_product.externalId}/{final_product.attributes.urlKey}",
        )
        offers.update(extract_offers(state))

    offers_compare_flow(
        product,
        offers=offers,
    )


def check_product_compare_flow(
    sb,
    product: Product,
):
    logger.info(f"Processing for {product.Product_name}")
    logger.info(f"Crawling at: {product.PRODUCT_COMPARE}")
    state = get_state(sb, product.PRODUCT_COMPARE)

    offers: dict[str, CrwlOffer] | None = None
    final_products: dict[str, FinalProduct] | None = None

    try:
        offers = extract_offers(state)
    except Exception:
        pass

    try:
        final_products = extract_ingame_category(state)
    except Exception:
        pass

    if offers is not None:
        try:
            logger.info("Offer Flow")
            offers_compare_flow(product, offers)
            return
        except Exception as e:
            logger.error(e)
            now = datetime.now()
            note_message = f"{last_update_message(now)}: ERROR: {e}"
            product.Note = note_message
            product.Last_update = last_update_message(now)
            product.update()
            return

    if final_products is not None:
        try:
            logger.info("Ingame Category Flow")
            ingame_category_compare_flow(sb, product, final_products)
            return
        except Exception as e:
            logger.error(e)
            now = datetime.now()
            note_message = f"{last_update_message(now)}: ERROR: {e}"
            product.Note = note_message
            product.Last_update = last_update_message(now)
            product.update()

    logger.error("Cannot extract from compare link!!!")
    now = datetime.now()
    note_message = (
        f"{last_update_message(now)}: Cannot extract data from compare link!!!"
    )
    product.Note = note_message
    product.Last_update = last_update_message(now)
    product.update()


def no_check_product_compare_flow(
    product: Product,
):
    product_min_price = product.min_price()
    product_max_price = product.max_price()
    stock = product.stock()

    my_offer_id = extract_offer_id_from_product_link(product.Product_link)

    update_by_price_and_stock(
        offer_id=my_offer_id, target_price=product_min_price, stock=stock
    )
    now = datetime.now()
    note_message = f"""{last_update_message(now)}:Giá đã cập nhật thành công; Price = {product_min_price}; Stock = {stock}; Pricemin = {product_min_price}, Pricemax = {product_max_price}"""

    product.Note = note_message
    product.Last_update = last_update_message(now)
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
