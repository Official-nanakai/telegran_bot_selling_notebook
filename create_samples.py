import json
from pathlib import Path

PRODUCTS_DIR = Path(__file__).resolve().parent / "products"
CATALOG_PATH = PRODUCTS_DIR / "catalog.json"

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000052 00000 n \n"
    b"0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n178\n%%EOF"
)


def main() -> None:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    for item in catalog:
        file_path = PRODUCTS_DIR / item["file"]
        if not file_path.exists():
            file_path.write_bytes(MINIMAL_PDF)
            print(f"Создан пример: {file_path.name}")

    print("Готово. Замените PDF в products/ на свои файлы.")


if __name__ == "__main__":
    main()
