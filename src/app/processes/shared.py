def extract_offer_id_from_product_link(link: str) -> str:
    """Extract offer ID from product link"""
    return link.split("/")[-1]
