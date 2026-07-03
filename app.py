import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from config import Product, get_admin_ids, get_bot_token, get_product, load_catalog_checked
from storage import save_purchase

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "Привет! Я продаю цифровые блокноты за Telegram Stars.\n\n"
    "Выберите блокнот в каталоге, оплатите звёздами и сразу получите PDF-файл.\n\n"
    "Команды:\n"
    "/catalog — каталог\n"
    "/help — помощь"
)

HELP_TEXT = (
    "Как купить блокнот:\n"
    "1. Откройте /catalog\n"
    "2. Нажмите «Купить» у нужного товара\n"
    "3. Подтвердите оплату Stars\n"
    "4. Получите PDF в этом чате\n\n"
    "Если оплата прошла, а файл не пришёл — напишите продавцу."
)


def catalog_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{product.title} — {product.price_stars} ⭐",
                callback_data=f"product:{product.id}",
            )
        ]
        for product in products
    ]
    return InlineKeyboardMarkup(rows)


def product_keyboard(product: Product) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Купить за Stars", callback_data=f"buy:{product.id}")],
            [InlineKeyboardButton("← Назад к каталогу", callback_data="catalog")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(WELCOME_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(HELP_TEXT)


async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    products = load_catalog_checked()
    await update.message.reply_text(
        "Каталог цифровых блокнотов:",
        reply_markup=catalog_keyboard(products),
    )


async def show_catalog(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = load_catalog_checked()
    await query.edit_message_text(
        "Каталог цифровых блокнотов:",
        reply_markup=catalog_keyboard(products),
    )


async def show_product(query, product: Product) -> None:
    text = (
        f"<b>{product.title}</b>\n\n"
        f"{product.description}\n\n"
        f"Цена: <b>{product.price_stars} ⭐</b>"
    )
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=product_keyboard(product),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    if query.data == "catalog":
        await show_catalog(query, context)
        return

    if query.data.startswith("product:"):
        product_id = query.data.removeprefix("product:")
        product = get_product(product_id)
        if not product:
            await query.edit_message_text("Товар не найден. Откройте /catalog снова.")
            return
        await show_product(query, product)
        return

    if query.data.startswith("buy:"):
        product_id = query.data.removeprefix("buy:")
        product = get_product(product_id)
        if not product:
            await query.edit_message_text("Товар не найден. Откройте /catalog снова.")
            return
        await send_invoice(query, product)


async def send_invoice(query, product: Product) -> None:
    chat_id = query.message.chat_id if query.message else query.from_user.id
    await query.get_bot().send_invoice(
        chat_id=chat_id,
        title=product.title,
        description=product.description,
        payload=f"notebook:{product.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=product.title, amount=product.price_stars)],
    )


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if not query:
        return

    payload = query.invoice_payload or ""
    if not payload.startswith("notebook:"):
        await query.answer(ok=False, error_message="Неизвестный товар.")
        return

    product_id = payload.removeprefix("notebook:")
    product = get_product(product_id)
    if not product:
        await query.answer(ok=False, error_message="Товар больше недоступен.")
        return

    if query.total_amount != product.price_stars:
        await query.answer(ok=False, error_message="Цена товара изменилась. Откройте каталог снова.")
        return

    await query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.successful_payment:
        return

    payment = message.successful_payment
    payload = payment.invoice_payload or ""
    product_id = payload.removeprefix("notebook:")
    product = get_product(product_id)

    if not product:
        await message.reply_text(
            "Оплата получена, но товар не найден. Напишите продавцу с деталями платежа."
        )
        return

    save_purchase(
        user_id=message.from_user.id,
        username=message.from_user.username,
        product_id=product.id,
        product_title=product.title,
        amount_stars=payment.total_amount,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
    )

    with product.file_path.open("rb") as notebook_file:
        await message.reply_document(
            document=notebook_file,
            filename=product.file,
            caption=f"Спасибо за покупку! Вот ваш блокнот: <b>{product.title}</b>",
            parse_mode="HTML",
        )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if update.effective_user.id not in get_admin_ids():
        await update.message.reply_text("Команда только для администратора.")
        return

    from config import PURCHASES_PATH

    if not PURCHASES_PATH.exists():
        await update.message.reply_text("Покупок пока нет.")
        return

    import json

    with PURCHASES_PATH.open(encoding="utf-8") as purchases_file:
        purchases = json.load(purchases_file)

    total_stars = sum(item["amount_stars"] for item in purchases)
    await update.message.reply_text(
        f"Покупок: {len(purchases)}\n"
        f"Выручка: {total_stars} ⭐"
    )


def build_application() -> Application:
    application = Application.builder().token(get_bot_token()).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("catalog", catalog_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    return application
