from datetime import datetime
import time
from app.models.crwl_models import OfferPrice
from app.utils.logger import logger
from app.utils.gsheet import worksheet
from app.processes.crwl import get_state, extract_offers, extract_ingame_category
from app.models.gsheet_model import Product
from app.processes.main_process import process

from seleniumbase import SB

from app.utils.kinguin_client import KinguinClient

with SB(headless=True, uc=True, uc_cdp=True) as sb:
    # url = "https://www.kinguin.net/ingame/c/297288/raid-shadow-legends-accounts?sort=price.lowestOffer%2CASC&page=1"
    sb.activate_cdp_mode("https://google.com")
    for index in range(4, 5):
        product = Product.get(worksheet, index)
        process(sb, product)

        time.sleep(2)

    # state = get_state(
    #     sb,
    #     "https://www.kinguin.net/category/301675/delta-force-top-up-global-24-300-delta-coins",
    # )
    # print(extract_offers(state))


# product = Product.get(worksheet, 4)
# print(product.model_dump_json(indent=4))
# print(product.min_price())
# print(product.max_price())
# print(product.stock())
# print(product.blacklist())

# client = KinguinClient()
# print(client.update_access_token().text)

# current_timestamp = datetime.now().timestamp()

# print(current_timestamp)
# print(datetime.fromtimestamp(current_timestamp))

# kinguin_client = KinguinClient()
# print(kinguin_client.get_offer("677eea113af4333987f50107"))
# print(
#     kinguin_client.calculate_merchant_commission_infomation(
#         kpc_product_id="66a36b450425a035454a7519", price=248
#     )
# )
# price = OfferPrice(
#     amount=187,
#     currency="EUR",
# )

# stock = 999

# kinguin_client.update_offer(
#     offer_id="677eea113af4333987f50107",
#     price=price,
#     declaredStock=stock,
# )
