from decimal import Decimal


def price_per_100g(package_price: Decimal | None, package_size_g: Decimal | None) -> Decimal | None:
    if package_price is None or package_size_g is None:
        return None
    if package_price < 0 or package_size_g <= 0:
        return None
    return package_price * Decimal(100) / package_size_g
