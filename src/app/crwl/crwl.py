from app.shared.consts import WINDOW_PRELOADEDSTATE_EXPRESSION
from .models import (
    CrwlOffer,
    FinalProduct,
    ExtractedFinalProduct,
    ExtractedOffer,
)
from .exceptions import CrwlError
from app.shared.decorators import retry_on_fail


@retry_on_fail(max_retries=3, sleep_interval=5)
def extract_state(
    sb,
):
    sb.cdp.get_page_source()
    state = sb.cdp.evaluate(WINDOW_PRELOADEDSTATE_EXPRESSION)
    if state is None:
        raise CrwlError("Cannot get data from web!!! State is None")
    return state


@retry_on_fail(max_retries=10, sleep_interval=5)
def get_state(
    sb,
    url: str,
):
    sb.cdp.get(url)
    sb.cdp.sleep(2)
    sb.cdp.get_page_source()
    state = extract_state(sb)
    return state


def dict_to_crwl_offer(
    offer: dict,
) -> CrwlOffer:
    return CrwlOffer.model_validate(offer)


def extract_offers(
    state: dict,
) -> dict[str, CrwlOffer]:
    offers_dict: dict[str, CrwlOffer] = {}

    offers_field = state["offers"]

    # Main offer
    main_offer = offers_field["mainOffer"]
    main_offer = dict_to_crwl_offer(main_offer)
    offers_dict[main_offer.id] = main_offer

    # Colection
    for offer in offers_field["collection"]:
        ofr = dict_to_crwl_offer(offer)
        if ofr.id in offers_dict:
            continue
        offers_dict[ofr.id] = ofr

    return offers_dict


def dict_to_final_product(
    fp: dict,
) -> FinalProduct:
    return FinalProduct.model_validate(fp)


def extract_ingame_category(
    state: dict,
) -> dict[str, FinalProduct]:
    final_products_dict: dict[str, FinalProduct] = {}

    ingame_category_field = state["ingameCategory"]
    for final_product in ingame_category_field["finalProducts"]["list"]:
        fp = dict_to_final_product(final_product)
        final_products_dict[fp.id] = fp

    return final_products_dict


def extract_offers_or_final_produce(
    sb,
    url: str,
) -> ExtractedOffer | ExtractedFinalProduct:
    state = get_state(sb, url)

    try:
        return ExtractedOffer(data=extract_offers(state))
    except Exception:
        pass

    try:
        return ExtractedFinalProduct(data=extract_ingame_category(state))
    except Exception:
        pass

    raise CrwlError("Cannot extract from compare link!!!")
