import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_DIR = BASE_DIR / "products"
CATALOG_PATH = PRODUCTS_DIR / "catalog.json"

if os.getenv("VERCEL"):
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = BASE_DIR / "data"

PURCHASES_PATH = DATA_DIR / "purchases.json"


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    description: str
    price_stars: int
    file: str

    @property
    def file_path(self) -> Path:
        return PRODUCTS_DIR / self.file


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен.")
    return token


def get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return set()
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


def get_webhook_secret() -> str:
    return os.getenv("WEBHOOK_SECRET", "").strip()


def get_setup_secret() -> str:
    return os.getenv("SETUP_SECRET", "").strip()


def get_webhook_url() -> str:
    explicit = os.getenv("WEBHOOK_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")

    vercel_url = os.getenv("VERCEL_URL", "").strip()
    if vercel_url:
        return f"https://{vercel_url}/api/webhook"

    raise RuntimeError("WEBHOOK_URL не задан. На Vercel он определяется автоматически.")


def load_catalog() -> list[Product]:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        items = json.load(catalog_file)

    products: list[Product] = []
    for item in items:
        product = Product(
            id=item["id"],
            title=item["title"],
            description=item["description"],
            price_stars=int(item["price_stars"]),
            file=item["file"],
        )
        products.append(product)
    return products


def validate_catalog_files(products: list[Product] | None = None) -> list[str]:
    items = products if products is not None else load_catalog()
    missing: list[str] = []
    for product in items:
        if not product.file_path.exists():
            missing.append(str(product.file_path))
    return missing


def load_catalog_checked() -> list[Product]:
    products = load_catalog()
    missing = validate_catalog_files(products)
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(
            "Не найдены файлы товаров:\n"
            f"{joined}\n\n"
            "Положите PDF в папку products/ или запустите: python create_samples.py"
        )
    return products


def get_product(product_id: str) -> Product | None:
    for product in load_catalog():
        if product.id == product_id:
            return product
    return None
