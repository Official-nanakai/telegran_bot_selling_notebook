import json
from datetime import datetime, timezone

from config import DATA_DIR, PURCHASES_PATH


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PURCHASES_PATH.exists():
        PURCHASES_PATH.write_text("[]", encoding="utf-8")


def save_purchase(
    *,
    user_id: int,
    username: str | None,
    product_id: str,
    product_title: str,
    amount_stars: int,
    telegram_payment_charge_id: str,
) -> None:
    _ensure_storage()
    with PURCHASES_PATH.open(encoding="utf-8") as purchases_file:
        purchases = json.load(purchases_file)

    purchases.append(
        {
            "user_id": user_id,
            "username": username,
            "product_id": product_id,
            "product_title": product_title,
            "amount_stars": amount_stars,
            "telegram_payment_charge_id": telegram_payment_charge_id,
            "purchased_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with PURCHASES_PATH.open("w", encoding="utf-8") as purchases_file:
        json.dump(purchases, purchases_file, ensure_ascii=False, indent=2)
