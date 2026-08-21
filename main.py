import html
import logging
from datetime import datetime, timedelta, timezone

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


BOT_TOKEN = "8533954781:AAFpmQerIa7XMCNH6wYZ8AWw629-FRNZGLs"

ADMIN_CHAT_ID = 8018004797  # например 123456789
LOG_CHAT_ID = -1004341731031

PRICE_USD = "5.00"
BANK_NAME = "OzonBank"
CARD_NUMBER = "2204320674827466"
SUPPORT_USERNAME = "@sam0end"

# ID приватного чата, доступ в который продаётся. Бот должен быть добавлен туда
# админом с правом "Invite Users via Link". Формат: -100xxxxxxxxxx (супергруппа/канал).
PRIVATE_CHAT_ID = -1003987249727
INVITE_LINK_TTL_MINUTES = 5

# Фото, которое показывается на каждом экране бота.
# ВАЖНО: обычная ссылка вида https://ibb.co/xxxx — это страница просмотра,
# Telegram по ней фото не подгрузит. Нужна ПРЯМАЯ ссылка на файл (i.ibb.co/...).
MAIN_PHOTO = "https://i.ibb.co/Rp3365nF/Chat-GPT-Image-21-2026-02-25-41.png"

WHATS_INCLUDED_TEXT = (
    '<b><tg-emoji emoji-id="6032644646587338669">🎁</tg-emoji> Хочешь попасть в ряды нашей тимы?</b>'
    '<tg-emoji emoji-id="5870930636742595124">📊</tg-emoji> <b>У нас есть всё необходимое для работы</b>\n'
    ' <tg-emoji emoji-id="5870930636742595124">📊</tg-emoji> <b> Cвой парсер Telegram подарков</b>\n'
    '  Мониторинг маркета → Сбор новых лотов → Отправка в группу\n\n'
    ' <tg-emoji emoji-id="6030400221232501136">🤖</tg-emoji> <b>Свой фишинг бот</b>\n'
    '  Готовый инструмент для сбора сессий (любая тематика)\n\n'
    ' <tg-emoji emoji-id="6037249452824072506">🔒</tg-emoji> <b>Свой скам гарант бот</b>\n'
    '  Безопасные P2P сделки в сторону воркера\n\n'
    ' <tg-emoji emoji-id="5904462880941545555">🪙</tg-emoji> <b>Цена входа:</b> <i>всего 5$</i>\n'
    ' <tg-emoji emoji-id="5983150113483134607">⏰</tg-emoji> <b>Окупается</b> <i>за 30 минут работы</i>\n\n'
    '<i><tg-emoji emoji-id="6041731551845159060">🎉</tg-emoji> Ждём тебя в тиме!</i>'
)

# --- CryptoBot (Crypto Pay API) ---
CRYPTO_PAY_TOKEN = "429463:AAthE30SrKvv14cN8tCYGggtTt3zdoCoOYB"
CRYPTO_ASSET = "USDT"
CRYPTO_PAY_API_URL = "https://pay.crypt.bot/api"

# --- xRocket (xRocket Pay API) ---
XROCKET_API_TOKEN = "9f7b24a24461c5df9f01bc574"
XROCKET_API_URL = "https://pay.xrocket.exchange"
XROCKET_CURRENCY = "USDT"

PROXY_URL = None

# ---------------------- Premium-эмодзи (custom_emoji_id) ----------------------
# ID из твоего набора. Иконку "Назад" сюда не подставляю — у неё не было ID
# в исходном списке (пришли его, и я добавлю).
EMOJI = {
    "lock": "6037249452824072506",       # 🔒 Купить / приватный доступ
    "info": "6028435952299413210",       # ℹ Что входит
    "megaphone": "6039422865189638057",  # 📣 Поддержка
    "cryptobot": "5260752406890711732",  # 👾 CryptoBot
    "money": "5904462880941545555",      # 🪙 xRocket
    "wallet": "5769126056262898415",     # 👛 Карта
    "link": "5769289093221454192",       # 🔗 Оплатить (переход по ссылке)
    "check": "5870633910337015697",      # ✅ Проверить / Подтвердить
    "cross": "5870657884844462243",      # ❌ Отклонить
    "clip": "6039451237743595514",       # 📎 Чек на проверку
}


def tg_emoji(key: str, fallback: str) -> str:
    """HTML-тег premium-эмодзи для текста сообщений (parse_mode=HTML)."""
    return f'<tg-emoji emoji-id="{EMOJI[key]}">{fallback}</tg-emoji>'


# ---------------------- Клавиатуры ----------------------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Купить доступ", callback_data="buy",
            style="primary", icon_custom_emoji_id=EMOJI["lock"],
        )],
        [InlineKeyboardButton(
            "Что входит", callback_data="whats_included",
            style="primary", icon_custom_emoji_id=EMOJI["info"],
        )],
        [InlineKeyboardButton(
            "Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
            style="primary", icon_custom_emoji_id=EMOJI["megaphone"],
        )],
    ])


def buy_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "CryptoBot", callback_data="pay_crypto",
            style="primary", icon_custom_emoji_id=EMOJI["cryptobot"],
        )],
        [InlineKeyboardButton(
            "xRocket", callback_data="pay_xrocket",
            style="primary", icon_custom_emoji_id=EMOJI["money"],
        )],
        [InlineKeyboardButton(
            "Карта", callback_data="pay_card",
            style="primary", icon_custom_emoji_id=EMOJI["wallet"],
        )],
        [InlineKeyboardButton("Назад", callback_data="back", style="primary")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back", style="primary")]])


def pay_keyboard(pay_url: str, check_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Оплатить", url=pay_url,
            style="primary", icon_custom_emoji_id=EMOJI["link"],
        )],
        [InlineKeyboardButton(
            "Проверить", callback_data=check_callback,
            style="primary", icon_custom_emoji_id=EMOJI["check"],
        )],
        [InlineKeyboardButton("Назад", callback_data="back", style="primary")],
    ])


def admin_review_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "Подтвердить", callback_data=f"approve_{user_id}",
            style="primary", icon_custom_emoji_id=EMOJI["check"],
        ),
        InlineKeyboardButton(
            "Отклонить", callback_data=f"decline_{user_id}",
            style="primary", icon_custom_emoji_id=EMOJI["cross"],
        ),
    ]])


# ---------------------- CryptoBot API ----------------------

async def create_crypto_invoice(amount: str, description: str):
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                f"{CRYPTO_PAY_API_URL}/createInvoice",
                headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN},
                json={"asset": CRYPTO_ASSET, "amount": amount, "description": description},
            )
            data = resp.json()
        except Exception as e:
            logger.warning(f"CryptoBot createInvoice request failed: {e}")
            return None
    if data.get("ok"):
        return data["result"]
    logger.warning(f"CryptoBot createInvoice error: {data}")
    return None


async def get_crypto_invoice_status(invoice_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{CRYPTO_PAY_API_URL}/getInvoices",
                headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN},
                params={"invoice_ids": invoice_id},
            )
            data = resp.json()
        except Exception as e:
            logger.warning(f"CryptoBot getInvoices request failed: {e}")
            return None
    if data.get("ok") and data["result"]["items"]:
        return data["result"]["items"][0]["status"]
    return None


# ---------------------- xRocket API ----------------------

async def create_xrocket_invoice(amount: float, description: str):
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                f"{XROCKET_API_URL}/tg-invoices",
                headers={"Rocket-Pay-Key": XROCKET_API_TOKEN},
                json={
                    "amount": amount,
                    "currency": XROCKET_CURRENCY,
                    "description": description,
                    "numPayments": 1,
                },
            )
            data = resp.json()
        except Exception as e:
            logger.warning(f"xRocket createInvoice request failed: {e}")
            return None
    if data.get("success"):
        return data["data"]
    logger.warning(f"xRocket createInvoice error: {data}")
    return None


async def get_xrocket_invoice_status(invoice_id):
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{XROCKET_API_URL}/tg-invoices/{invoice_id}",
                headers={"Rocket-Pay-Key": XROCKET_API_TOKEN},
            )
            data = resp.json()
        except Exception as e:
            logger.warning(f"xRocket getInvoice request failed: {e}")
            return None
    if data.get("success"):
        return data["data"]["status"]
    return None


# ---------------------- Экраны (текст+фото под каждый callback) ----------------------

def screen_start() -> str:
    return (
        f'{tg_emoji("lock", "🔒")} <b>Forever Team</b>\n\n'
        '<blockquote>'
        '<b>Добро пожаловать в наш бот!</b>\n\n'
        'Здесь ты найдёшь всю актуальную информацию '
        'о нашей команде и приватном доступе.\n\n'
        f'{tg_emoji("info", "ℹ️")} <b>Стоимость доступа — 5$</b>\n'
        f'{tg_emoji("megaphone", "📣")} Вся актуальная информация '
        'находится в кнопках ниже.'
        '</blockquote>\n\n'
        '<b>Выбери действие:</b>'
    )


def screen_buy() -> str:
    return f'{tg_emoji("lock", "🔒")} <b>Доступ — {PRICE_USD}$</b>\n\nСпособ оплаты:'


def screen_whats_included() -> str:
    return f'{tg_emoji("info", "ℹ")} <b>Что входит</b>\n\n{WHATS_INCLUDED_TEXT}'


def screen_pay_card() -> str:
    return (
        f'{tg_emoji("wallet", "💳")} <b>Перевод на карту</b>\n\n'
        f"Цена: {PRICE_USD}$\n"
        f"Банк: {BANK_NAME}\n"
        f"Карта: {CARD_NUMBER}\n\n"
        f"Пришли сюда фото чека после оплаты."
    )


def screen_crypto_invoice_created() -> str:
    return f'{tg_emoji("cryptobot", "💰")} <b>Счёт создан — {PRICE_USD} {CRYPTO_ASSET}</b>\n\nОплати и нажми «Проверить».'


def screen_xrocket_invoice_created() -> str:
    return f'{tg_emoji("money", "🚀")} <b>Счёт создан — {PRICE_USD} {XROCKET_CURRENCY}</b>\n\nОплати и нажми «Проверить».'


def screen_paid() -> str:
    return f'{tg_emoji("check", "✅")} <b>Оплата подтверждена!</b>\nСсылка на вход придёт следующим сообщением.'


def screen_invite_link(link: str) -> str:
    return (
        f'{tg_emoji("lock", "🔒")} <b>Вход в приватный чат</b>\n\n'
        f"{link}\n\n"
        f"Ссылка одноразовая и действует {INVITE_LINK_TTL_MINUTES} минут."
    )


def screen_pending() -> str:
    return "Оплата ещё не поступила. Оплати счёт и нажми проверку ещё раз."


def screen_expired() -> str:
    return "Счёт истёк или не найден. Создай новый через «Купить доступ»."


def screen_invoice_failed() -> str:
    return f"Не удалось создать счёт. Попробуй позже или напиши в поддержку {SUPPORT_USERNAME}."


# ---------------------- Одноразовая ссылка в приватный чат ----------------------

async def grant_access(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> None:
    """Создаёт одноразовую инвайт-ссылку на PRIVATE_CHAT_ID (действует
    INVITE_LINK_TTL_MINUTES минут, member_limit=1) и отправляет пользователю."""
    if not PRIVATE_CHAT_ID:
        logger.warning("PRIVATE_CHAT_ID не задан — ссылка не создана.")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Оплата подтверждена, но ссылка на чат не настроена. Напиши в поддержку {SUPPORT_USERNAME}",
        )
        return
    expire_date = datetime.now(timezone.utc) + timedelta(minutes=INVITE_LINK_TTL_MINUTES)
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHAT_ID,
            member_limit=1,
            expire_date=expire_date,
        )
    except Exception as e:
        logger.warning(f"Не удалось создать инвайт-ссылку: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Оплата подтверждена, но не получилось создать ссылку. Напиши в поддержку {SUPPORT_USERNAME}",
        )
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text=screen_invite_link(invite.invite_link),
        parse_mode="HTML",
    )
    if LOG_CHAT_ID:
        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=f"Выдана инвайт-ссылка пользователю id {user_id}",
        )


# ---------------------- Хендлеры ----------------------

async def show_screen(update: Update, text: str, reply_markup: InlineKeyboardMarkup):
    """Показать экран: новое фото-сообщение (первый /start) либо правка подписи
    у уже отправленного фото-сообщения (все остальные переходы)."""
    if update.message:
        await update.message.reply_photo(
            photo=MAIN_PHOTO, caption=text, parse_mode="HTML", reply_markup=reply_markup,
        )
    else:
        await update.callback_query.edit_message_caption(
            caption=text, parse_mode="HTML", reply_markup=reply_markup,
        )


async def log_new_visit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not LOG_CHAT_ID:
        return
    user = update.effective_user
    text = (
        f"Зашёл в бота\n"
        f"Имя: {user.full_name}\n"
        f"Username: @{user.username if user.username else '—'}\n"
        f"ID: {user.id}\n"
        f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    try:
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=text)
    except Exception as e:
        logger.warning(f"Не удалось отправить лог: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await log_new_visit(update, context)
    await show_screen(update, screen_start(), main_menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "buy":
        await show_screen(update, screen_buy(), buy_menu_keyboard())

    # ---------- CryptoBot ----------
    elif data == "pay_crypto":
        await query.edit_message_caption(caption="Создаю счёт на оплату…", parse_mode="HTML")
        user = update.effective_user
        invoice = await create_crypto_invoice(
            amount=PRICE_USD,
            description=f"Доступ для {user.full_name} (id {user.id})",
        )
        if not invoice:
            await show_screen(update, screen_invoice_failed(), back_keyboard())
            return
        context.user_data["crypto_invoice_id"] = invoice["invoice_id"]
        await show_screen(
            update,
            screen_crypto_invoice_created(),
            pay_keyboard(invoice["pay_url"], "check_crypto"),
        )

    elif data == "check_crypto":
        invoice_id = context.user_data.get("crypto_invoice_id")
        if not invoice_id:
            await show_screen(update, "Счёт не найден, создай новый через «Купить доступ».", back_keyboard())
            return
        status = await get_crypto_invoice_status(invoice_id)
        if status == "paid":
            await show_screen(update, screen_paid(), back_keyboard())
            user = update.effective_user
            if LOG_CHAT_ID:
                await context.bot.send_message(
                    chat_id=LOG_CHAT_ID,
                    text=f"Оплата (CryptoBot) прошла: {user.full_name} (id {user.id})",
                )
            await grant_access(context, user_id=user.id, chat_id=update.effective_chat.id)
        elif status == "active":
            await show_screen(
                update, screen_pending(),
                pay_keyboard(query.message.reply_markup.inline_keyboard[0][0].url, "check_crypto"),
            )
        else:
            await show_screen(update, screen_expired(), back_keyboard())

    # ---------- xRocket ----------
    elif data == "pay_xrocket":
        await query.edit_message_caption(caption="Создаю счёт на оплату…", parse_mode="HTML")
        user = update.effective_user
        invoice = await create_xrocket_invoice(
            amount=float(PRICE_USD),
            description=f"Доступ для {user.full_name} (id {user.id})",
        )
        if not invoice:
            await show_screen(update, screen_invoice_failed(), back_keyboard())
            return
        context.user_data["xrocket_invoice_id"] = invoice["id"]
        await show_screen(
            update,
            screen_xrocket_invoice_created(),
            pay_keyboard(invoice["link"], "check_xrocket"),
        )

    elif data == "check_xrocket":
        invoice_id = context.user_data.get("xrocket_invoice_id")
        if not invoice_id:
            await show_screen(update, "Счёт не найден, создай новый через «Купить доступ».", back_keyboard())
            return
        status = await get_xrocket_invoice_status(invoice_id)
        if status == "paid":
            await show_screen(update, screen_paid(), back_keyboard())
            user = update.effective_user
            if LOG_CHAT_ID:
                await context.bot.send_message(
                    chat_id=LOG_CHAT_ID,
                    text=f"Оплата (xRocket) прошла: {user.full_name} (id {user.id})",
                )
            await grant_access(context, user_id=user.id, chat_id=update.effective_chat.id)
        elif status == "active":
            await show_screen(
                update, screen_pending(),
                pay_keyboard(query.message.reply_markup.inline_keyboard[0][0].url, "check_xrocket"),
            )
        else:
            await show_screen(update, screen_expired(), back_keyboard())

    # ---------- Перевод на карту ----------
    elif data == "pay_card":
        context.user_data["awaiting_receipt"] = True
        await show_screen(update, screen_pay_card(), back_keyboard())

    elif data == "whats_included":
        await show_screen(update, screen_whats_included(), back_keyboard())

    elif data == "back":
        await start(update, context)

    elif data.startswith("approve_") or data.startswith("decline_"):
        if update.effective_chat.id != ADMIN_CHAT_ID:
            return
        target_user_id = int(data.split("_", 1)[1])
        old_caption = query.message.caption or ""
        if data.startswith("approve_"):
            await context.bot.send_message(chat_id=target_user_id, text="Оплата подтверждена! Ссылка на вход придёт следующим сообщением.")
            await grant_access(context, user_id=target_user_id, chat_id=target_user_id)
            await query.edit_message_caption(caption=old_caption + "\n\nПОДТВЕРЖДЕНО")
        else:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Оплата не подтверждена. Напиши в поддержку {SUPPORT_USERNAME}",
            )
            await query.edit_message_caption(caption=old_caption + "\n\nОТКЛОНЕНО")


async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_receipt"):
        return
    user = update.effective_user
    photo = update.message.photo[-1]
    caption = (
        f'{tg_emoji("clip", "📎")} <b>Новый чек на проверку</b>\n'
        f"Имя: {html.escape(user.full_name)}\n"
        f"Username: @{html.escape(user.username) if user.username else '—'}\n"
        f"ID: {user.id}"
    )
    if ADMIN_CHAT_ID:
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=photo.file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=admin_review_keyboard(user.id),
        )
    await update.message.reply_text("Чек получен и отправлен на проверку. Жди подтверждения от администратора.")
    context.user_data["awaiting_receipt"] = False


def main():
    builder = Application.builder().token(BOT_TOKEN)
    if PROXY_URL:
        builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, receipt_photo_handler))

    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
