from app.utils.logger import logger
from app.utils.gsheet import worksheet

from seleniumbase import SB

with SB(headless=True, uc=True, uc_cdp=True) as sb:
    url = "https://www.kinguin.net/category/255577/7-days-to-die-pc-account"
    sb.activate_cdp_mode(url)
    print(sb.cdp.evaluate("window._preloadedState")["offers"])
    sb.sleep(2)
