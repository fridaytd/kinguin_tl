import random
from datetime import datetime

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
from ..utils.price_utils import (
    int_to_float_price,
    priceiwtr_to_price,
    price_to_priceiwtr,
    unit_price_to_priceiwtr,
    to_real_unit_price,
    back_to_abstract_unit_price,
)
from ..utils.update_messages import (
    update_with_comparing_seller,
    update_with_min_price,
)
from ..models.api_models import Offer
from ..models.prices import (
    RealUnitPrice,
    RealUnitPricePerUnitStock,
    APIUnitPrice,
    PriceCustomerPay,
    PriceIWTR,
)
from app.service.data_cache import CachedRow, get_cache
from app.utils.date_time import formated_datetime


def update_cache_note(cached_row: CachedRow, note: str):
    """Update note and last_update in cache"""
    now = datetime.now()
    cache = get_cache()
    cache.update_fields(
        index=cached_row.index, 
        note=note, 
        last_update=formated_datetime(now)
    )


def extract_offer_id_from_product_link(link: str) -> str:
    return link.split("/")[-1]


def update_offer(
    offer_id: str,
    price: PriceBase,
    declaredStock: int,
    min_quantity: int | None,
):
    kinguin_client.update_offer(
        offer_id=offer_id,
        price=price,
        declaredStock=declaredStock,
        min_quantity=min_quantity,
    )
    return


def calculate_unit_price_change_by_min_offer(
    cached_row: CachedRow,
    product_min_real_unit_price_per_unit_stock: RealUnitPricePerUnitStock,
    product_max_real_unit_price_per_unit_stock: RealUnitPricePerUnitStock | None,
    compare_real_unit_price_per_unit_stock: RealUnitPricePerUnitStock,
) -> RealUnitPricePerUnitStock:
    new_min_unit_price_random = (
        compare_real_unit_price_per_unit_stock.amount - cached_row.DONGIAGIAM_MAX
        if compare_real_unit_price_per_unit_stock.amount - cached_row.DONGIAGIAM_MAX
        >= product_min_real_unit_price_per_unit_stock.amount
        else product_min_real_unit_price_per_unit_stock.amount
    )
    new_max_unit_price_random = (
        compare_real_unit_price_per_unit_stock.amount - cached_row.DONGIAGIAM_MIN
        if compare_real_unit_price_per_unit_stock.amount - cached_row.DONGIAGIAM_MIN
        >= product_min_real_unit_price_per_unit_stock.amount
        else product_min_real_unit_price_per_unit_stock.amount
    )
    new_unit_price_change = round(
        random.uniform(new_min_unit_price_random, new_max_unit_price_random),
        cached_row.DONGIA_LAMTRON,
    )

    return RealUnitPricePerUnitStock(
        amount=new_unit_price_change, unit_stock=1
    )


def offers_compare_flow(
    cached_row: CachedRow,
    my_offer: Offer,
    offers: dict[str, CrwlOffer],
    check_mode: str,
):
    valid_crwl_offers: dict[str, CrwlOffer] = {}

    # Get product data from cache (no API calls!)
    _product_min_price: float = cached_row.min_price_value
    product_min_real_unit_price_per_unit_stock = RealUnitPricePerUnitStock(
        amount=_product_min_price,
        unit_stock=1,  # Adjust based on your needs
    )

    _product_max_price: float | None = cached_row.max_price_value
    product_max_real_unit_price_per_unit_stock: RealUnitPricePerUnitStock | None = (
        RealUnitPricePerUnitStock(
            amount=_product_max_price,
            unit_stock=1,
        )
        if _product_max_price
        else None
    )
    blacklist = cached_row.blacklist_value
    stock_without_unit = cached_row.stock_value

    logger.info(
        f"Product min unit price: {product_min_real_unit_price_per_unit_stock.amount}"
    )
    logger.info(
        f"Product max unit price: {product_max_real_unit_price_per_unit_stock.amount if product_max_real_unit_price_per_unit_stock else None}"
    )

    min_unit_price_offer: CrwlOffer | None = None

    # Filter valid offer and find min unit price offer
    for offer_id, offer in offers.items():
        # Convert to the same unit on sheet
        offer_api_unit_price: APIUnitPrice = APIUnitPrice(amount=offer.unitPrice)
        offer_real_unit_price: RealUnitPrice = offer_api_unit_price.to_real_unit_price()
        offer_real_unit_price_per_unit_stock = (
            offer_real_unit_price.to_unit_price_per_unit_stock(unit_stock=1)
        )

        if offer.seller.name not in blacklist:
            if (
                product_max_real_unit_price_per_unit_stock
                and product_min_real_unit_price_per_unit_stock.amount
                <= offer_real_unit_price_per_unit_stock.amount
                <= product_max_real_unit_price_per_unit_stock.amount
            ) or (
                product_max_real_unit_price_per_unit_stock is None
                and product_min_real_unit_price_per_unit_stock.amount
                <= offer_real_unit_price_per_unit_stock.amount
            ):
                valid_crwl_offers[offer_id] = offer
                if (
                    min_unit_price_offer is None
                    or offer.unitPrice < min_unit_price_offer.unitPrice
                ):
                    min_unit_price_offer = offer

    # Determine target price
    target_priceiwtr = None
    note_message = ""
    
    if min_unit_price_offer is None:
        if product_max_real_unit_price_per_unit_stock:
            logger.info("Update by max price")
            # Round target real unit price per unit stock
            product_max_real_unit_price_per_unit_stock.amount = round(
                product_max_real_unit_price_per_unit_stock.amount,
                cached_row.DONGIA_LAMTRON,
            )
            # Convert to api unit price
            target_api_unit_price: APIUnitPrice = (
                product_max_real_unit_price_per_unit_stock.to_api_unit_price()
            )
            # Convert to price customer pay
            target_price_customer_pay: PriceCustomerPay = (
                target_api_unit_price.to_price_customer_pay(
                    min_quantity_per_order=1  # Adjust if needed
                )
            )
            # Convert to price I want to receive
            target_priceiwtr = target_price_customer_pay.to_priceiwtr(
                commission_rule=my_offer.commissionRule
            )
            note_message, last_update_message = update_with_min_price(
                price=target_price_customer_pay.to_real_price().amount,
                priceiwtr=target_priceiwtr.to_real_price().amount,
                unit_price=product_max_real_unit_price_per_unit_stock.amount,
                stock=stock_without_unit,
                min_quantity=None,  # Adjust if needed
                unit_stock=1,
                price_min=product_min_real_unit_price_per_unit_stock.amount,
                price_max=product_max_real_unit_price_per_unit_stock.amount,
            )

        else:
            logger.info("Update by min price")
            # Round target real unit price per unit stock
            product_min_real_unit_price_per_unit_stock.amount = round(
                product_min_real_unit_price_per_unit_stock.amount,
                cached_row.DONGIA_LAMTRON,
            )
            # Convert to api unit price
            target_api_unit_price: APIUnitPrice = (
                product_min_real_unit_price_per_unit_stock.to_api_unit_price()
            )
            # Convert to price customer pay
            target_price_customer_pay: PriceCustomerPay = (
                target_api_unit_price.to_price_customer_pay(
                    min_quantity_per_order=1
                )
            )
            # Convert to price I want to receive
            target_priceiwtr = target_price_customer_pay.to_priceiwtr(
                commission_rule=my_offer.commissionRule
            )
            note_message, last_update_message = update_with_min_price(
                price=target_price_customer_pay.to_real_price().amount,
                priceiwtr=target_priceiwtr.to_real_price().amount,
                unit_price=product_min_real_unit_price_per_unit_stock.amount,
                stock=stock_without_unit,
                min_quantity=None,
                unit_stock=1,
                price_min=product_min_real_unit_price_per_unit_stock.amount,
                price_max=None,
            )
    else:
        logger.info(f"Found competitor: {min_unit_price_offer.seller.name}")

        # Convert competitor price to same unit
        compare_api_unit_price: APIUnitPrice = APIUnitPrice(
            amount=min_unit_price_offer.unitPrice
        )
        compare_real_unit_price: RealUnitPrice = (
            compare_api_unit_price.to_real_unit_price()
        )
        compare_real_unit_price_per_unit_stock: RealUnitPricePerUnitStock = (
            compare_real_unit_price.to_unit_price_per_unit_stock(unit_stock=1)
        )

        # Check mode 2: If already lower than competitor, don't update
        if check_mode == "2":
            # Get current price from my offer
            current_priceiwtr = PriceIWTR(amount=my_offer.price.amount)
            current_price_customer_pay = current_priceiwtr.to_price_customer_pay(
                commission_rule=my_offer.commissionRule
            )
            current_api_unit_price = current_price_customer_pay.to_api_unit_price(
                min_quantity_per_order=1
            )
            current_real_unit_price = current_api_unit_price.to_real_unit_price()
            current_real_unit_price_per_unit_stock = (
                current_real_unit_price.to_unit_price_per_unit_stock(unit_stock=1)
            )

            if (
                current_real_unit_price_per_unit_stock.amount
                < compare_real_unit_price_per_unit_stock.amount
            ):
                logger.info(
                    f"Mode 2: Current price ({current_real_unit_price_per_unit_stock.amount}) "
                    f"already lower than competitor ({compare_real_unit_price_per_unit_stock.amount}). "
                    f"No update needed."
                )
                note_message = (
                    f"Giá đã tốt hơn đối thủ, không cần cập nhật! "
                    f"Current={current_real_unit_price_per_unit_stock.amount:.2f}, "
                    f"Competitor={compare_real_unit_price_per_unit_stock.amount:.2f} "
                    f"({min_unit_price_offer.seller.name})"
                )
                update_cache_note(cached_row, note_message)
                return

        # Calculate new price based on competitor
        logger.info(f"Update price by price of {min_unit_price_offer.seller.name}")
        
        target_real_unit_price_per_unit_stock = calculate_unit_price_change_by_min_offer(
            cached_row=cached_row,
            product_min_real_unit_price_per_unit_stock=product_min_real_unit_price_per_unit_stock,
            product_max_real_unit_price_per_unit_stock=product_max_real_unit_price_per_unit_stock,
            compare_real_unit_price_per_unit_stock=compare_real_unit_price_per_unit_stock,
        )
        logger.info(target_real_unit_price_per_unit_stock.amount)
        target_api_unit_price = (
            target_real_unit_price_per_unit_stock.to_api_unit_price()
        )
        target_price_customer_pay = target_api_unit_price.to_price_customer_pay(
            min_quantity_per_order=1
        )
        target_priceiwtr = target_price_customer_pay.to_priceiwtr(
            commission_rule=my_offer.commissionRule
        )
        note_message, last_update_message = update_with_comparing_seller(
            price=target_price_customer_pay.to_real_price().amount,
            priceiwtr=target_priceiwtr.to_real_price().amount,
            unit_price=target_real_unit_price_per_unit_stock.amount,
            stock=stock_without_unit,
            unit_stock=1,
            min_quantity=None,
            price_min=product_min_real_unit_price_per_unit_stock.amount,
            price_max=product_max_real_unit_price_per_unit_stock.amount
            if product_max_real_unit_price_per_unit_stock
            else None,
            comparing_seller=min_unit_price_offer.seller.name,
            comparing_seller_actual_price=int_to_float_price(
                price_to_priceiwtr(
                    min_unit_price_offer.price.amount, my_offer.commissionRule
                )
            ),
            comparing_seller_unit_price=to_real_unit_price(
                min_unit_price_offer.unitPrice
            ),
        )

    # Update offer if we have a target price
    if target_priceiwtr:
        update_offer(
            offer_id=my_offer.id,
            price=PriceBase(
                amount=target_priceiwtr.amount,
                currency=CURRENCY,
            ),
            declaredStock=stock_without_unit,
            min_quantity=None,
        )
    
    # Update cache
    if note_message:
        update_cache_note(cached_row, note_message)


def ingame_category_compare_flow(
    sb,
    cached_row: CachedRow,
    my_offer: Offer,
    final_products: dict[str, FinalProduct],
    check_mode: str,
):
    product_min_unit_price = cached_row.min_price_value
    product_max_unit_price = cached_row.max_price_value

    valid_final_products: dict[str, FinalProduct] = {}

    for product_id, final_product in final_products.items():
        real_offer_unit_price = to_real_unit_price(
            final_product.ingameAttributes.unitPrice
        )
        if (
            product_max_unit_price
            and product_min_unit_price
            <= real_offer_unit_price
            <= product_max_unit_price
        ) or (
            product_max_unit_price is None
            and product_min_unit_price <= real_offer_unit_price
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
        cached_row=cached_row,
        my_offer=my_offer,
        offers=offers,
        check_mode=check_mode,
    )


def check_product_compare_flow(
    sb,
    cached_row: CachedRow,
    check_mode: str,
):
    logger.info(f"Processing for {cached_row.Product_name}")
    logger.info(f"Crawling at: {cached_row.PRODUCT_COMPARE}")

    my_offer_id = extract_offer_id_from_product_link(cached_row.Product_link)

    my_offer = kinguin_client.get_offer(offer_id=my_offer_id)

    extracted_data = extract_offers_or_final_produce(sb, cached_row.PRODUCT_COMPARE)

    if isinstance(extracted_data, ExtractedOffer):
        offers_compare_flow(
            cached_row=cached_row, 
            my_offer=my_offer, 
            offers=extracted_data.data,
            check_mode=check_mode,
        )
    else:
        ingame_category_compare_flow(
            sb,
            cached_row=cached_row,
            my_offer=my_offer,
            final_products=extracted_data.data,
            check_mode=check_mode,
        )


def no_check_product_compare_flow(
    cached_row: CachedRow,
):
    product_min_unit_price = cached_row.min_price_value
    product_max_unit_price = cached_row.max_price_value
    stock = cached_row.stock_value

    real_stock = stock  # Adjust if needed

    abstract_unit_price = back_to_abstract_unit_price(
        real_unit_price=product_min_unit_price
    )

    my_offer_id = extract_offer_id_from_product_link(cached_row.Product_link)
    my_offer = kinguin_client.get_offer(offer_id=my_offer_id)

    target_priceiwtr = unit_price_to_priceiwtr(
        unit_price=abstract_unit_price,
        min_quantity=None,
        commission_rule=my_offer.commissionRule,
    )

    update_offer(
        offer_id=my_offer_id,
        declaredStock=real_stock,
        price=PriceBase(amount=target_priceiwtr, currency=CURRENCY),
        min_quantity=None,
    )

    note_message, last_update_message = update_with_min_price(
        price=int_to_float_price(
            priceiwtr_to_price(target_priceiwtr, my_offer.commissionRule)
        ),
        priceiwtr=int_to_float_price(target_priceiwtr),
        unit_price=product_min_unit_price,
        stock=stock,
        min_quantity=None,
        unit_stock=1,
        price_min=product_min_unit_price,
        price_max=product_max_unit_price,
    )

    # Update cache instead of calling product.update()
    update_cache_note(cached_row, note_message)


def process(
    sb,
    cached_row: CachedRow,
):
    check_mode = cached_row.CHECK_PRODUCT_COMPARE
    
    if check_mode != "0":
        logger.info(f"Mode {check_mode}: Compare product flow")
        check_product_compare_flow(sb, cached_row, check_mode)
    else:
        logger.info("Mode 0: No comparison, updating by min price")
        no_check_product_compare_flow(cached_row)