from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from aiogram.types import FSInputFile
from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.text import escape_html, safe_edit_or_send


def _pluralize_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} день"
    if n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return f"{n} дня"
    return f"{n} дней"


def tariff_product_keyboard(tariffs, *, key_id: Optional[int] = None):
    import os
    import config

    builder = InlineKeyboardBuilder()
    labels = {
        "economy": "📉 Эконом — от 78 ₽/мес",
        "standard": "👤 Стандарт — от 122 ₽/мес",
        "family": "👨‍👩‍👧‍👦 Семейный — от 282 ₽/мес",
    }
    available = {str(item.get("product_code") or "standard") for item in tariffs}
    for code in ("economy", "standard", "family"):
        if code in available:
            suffix = str(key_id) if key_id is not None else "new"
            builder.row(InlineKeyboardButton(text=labels[code], callback_data=f"select_product:{code}:{suffix}"))
    webapp_url = os.getenv("WEBAPP_URL", config.SUBSCRIPTION_URL).rstrip("/")
    builder.row(InlineKeyboardButton(
        text="⚙️ Создать свой тариф",
        web_app=WebAppInfo(url=f"{webapp_url}/app?screen=custom-tariff"),
        style="primary",
    ))
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="start"))
    return builder.as_markup()


def build_tariff_catalog_text(tariffs) -> str:
    """Canonical product copy; legacy editable text must not hide products."""
    details = {
        "economy": ("📉", "Эконом", "основной трафик безлимитный · без LTE · 2 устройства"),
        "standard": ("👤", "Стандарт", "основной трафик безлимитный · 45 ГБ LTE · 3 устройства"),
        "family": ("👨‍👩‍👧‍👦", "Семейный", "основной трафик безлимитный · 115 ГБ обхода · 8 устройств"),
    }
    by_code = {}
    for item in tariffs:
        code = str(item.get("product_code") or "standard")
        by_code.setdefault(code, []).append(item)
    blocks = ["🌍 <b>Выберите подходящий тариф VPN:</b>"]
    for code in ("economy", "standard", "family"):
        products = by_code.get(code)
        if not products:
            continue
        icon, title, description = details[code]
        monthly = min(
            round(float(item.get("price_rub") or 0) / max(1, int(item.get("period_months") or 1)))
            for item in products if float(item.get("price_rub") or 0) > 0
        )
        blocks.append(f"{icon} <b>{title}</b>\n{description}\n💰 от <b>{monthly} ₽/мес</b>")
    return "\n\n".join(blocks)


def _format_payment_context_text(
    tariff: Dict[str, Any],
    key: Optional[Dict[str, Any]] = None,
    discount_rub: int = 0,
    intro_text: Optional[str] = None,
    auto_renew: bool = False,
    recurring_available: bool = False,
) -> str:
    is_renew = key is not None
    title = "⚡ <b>Продление подписки</b>" if is_renew else "💳 <b>Оплата подписки</b>"
    header_lines = [title]

    if tariff.get('price_rub') and tariff['price_rub'] > 0:
        base_price = float(tariff['price_rub'])
        final_price = max(0, base_price - discount_rub)
        if discount_rub > 0:
            price_text = f"<s>{base_price:g} ₽</s> → {final_price:g} ₽"
        else:
            price_text = f"{base_price:g} ₽"
    else:
        price_usd = tariff['price_cents'] / 100
        price_str = f"{price_usd:g}".replace('.', ',')
        price_text = f"${price_str}"

    months = max(1, round(int(tariff['duration_days']) / 30))
    monthly = ""
    if tariff.get('price_rub') and months > 1:
        monthly = f" · {round(float(tariff['price_rub']) / months):g} ₽/мес"
    block_lines = [
        f"📅 Срок: <b>{months} мес.</b>",
        f"💳 К оплате: <b>{price_text}</b>{monthly}",
    ]

    if discount_rub > 0 and tariff.get('price_rub'):
        block_lines.append(f"Скидка по промокоду: {discount_rub} ₽")

    text = "\n\n".join(header_lines + [
        f"<blockquote>{chr(10).join(block_lines)}</blockquote>",
        "⚡ Оплата откроется сразу в приложении банка через СБП.\n"
        "После оплаты подписка продлится автоматически.",
    ])
    text += "\n\n<blockquote>🔁 Режим автопродления вы выберете на следующем шаге после способа оплаты.</blockquote>"
    if intro_text:
        return intro_text.strip() + "\n\n" + text
    return text


async def show_tariff_selection_screen(message, telegram_id: int, key_id: Optional[int] = None, order_id: Optional[str] = None) -> bool:
    from bot.keyboards.admin import home_only_kb
    from bot.keyboards.user import tariff_select_kb, back_and_home_kb
    from bot.utils.groups import get_tariffs_for_renewal
    from bot.utils.message_editor import get_message_data
    from database.requests import get_all_tariffs, get_key_details_for_user

    if key_id is None:
        tariffs = get_all_tariffs(include_hidden=False)
        if not tariffs:
            await safe_edit_or_send(
                message,
                '💳 <b>Купить подписку</b>\n\n😔 К сожалению, сейчас нет доступных тарифов.\n\nПопробуйте позже или обратитесь в поддержку.',
                reply_markup=home_only_kb()
            )
            return False

        tariff_select_data = get_message_data('tariff_select_text', '')
        photo_file_id = tariff_select_data.get('photo_file_id')
        text = build_tariff_catalog_text(tariffs)

        default_cover = Path(__file__).resolve().parents[1] / "assets" / "arc-payment-v1.png"
        await safe_edit_or_send(
            message,
            text,
            photo=photo_file_id or (FSInputFile(default_cover) if default_cover.exists() else None),
            reply_markup=tariff_product_keyboard(tariffs)
        )
        return True

    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        return False

    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    if not tariffs:
        await safe_edit_or_send(
            message,
            '💳 <b>Продление подписки</b>\n\n😔 Нет доступных тарифов.\nПопробуйте позже.',
            reply_markup=back_and_home_kb(back_callback=f'key:{key_id}')
        )
        return False

    if key['expires_at']:
        from bot.utils.datetime_utils import utc_to_local
        expires_dt_utc = datetime.fromisoformat(key['expires_at'])
        expires_dt_local = utc_to_local(expires_dt_utc)
        expires = expires_dt_local.strftime('%d-%m-%Y')
        delta = expires_dt_local - datetime.now(expires_dt_local.tzinfo)
        days_left = max(1, delta.days + (1 if delta.seconds > 0 else 0)) if delta.total_seconds() > 0 else 0
    else:
        expires = '—'
        days_left = 0

    days_text = _pluralize_days(days_left) if days_left > 0 else 'истек'
    text = (
        "⚡ <b>Продлить подписку</b>\n\n"
        f"Сейчас осталось: <b>{days_text}</b>\n"
        f"Доступ оплачен до: <b>{expires}</b>\n\n"
        "<blockquote>Новый срок прибавится к текущему — оставшиеся дни не сгорят.</blockquote>\n\n"
        "Сначала выберите тариф:"
    )

    default_cover = Path(__file__).resolve().parents[1] / "assets" / "arc-payment-v1.png"
    await safe_edit_or_send(
        message,
        text,
        photo=FSInputFile(default_cover) if default_cover.exists() else None,
        reply_markup=tariff_product_keyboard(tariffs, key_id=key_id)
    )
    return True


async def show_payment_method_selection_screen(
    message,
    telegram_id: int,
    tariff_id: int,
    key_id: Optional[int] = None,
    order_id: Optional[str] = None,
    intro_text: Optional[str] = None,
    has_promocode: bool = False,
) -> Optional[Dict[str, Any]]:
    from bot.keyboards.admin import home_only_kb
    from bot.keyboards.user import payment_method_kb, renew_payment_method_kb, back_and_home_kb
    from bot.utils.message_editor import get_message_data
    from database.requests import (
        get_key_details_for_user, get_setting, get_tariff_by_id, get_user_balance,
        get_user_internal_id, is_cards_enabled,
        is_demo_payment_enabled, is_referral_enabled,
        is_yookassa_qr_configured, get_referral_reward_type,
        prepare_payment_order,
    )

    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        return None

    key = None
    if key_id is not None:
        key = get_key_details_for_user(key_id, telegram_id)
        if not key:
            return None

    crypto_configured = False
    crypto_mode = 'disabled'
    stars_enabled = False  # Stars убраны из пользовательского UI ArcVPN.
    cards_enabled = is_cards_enabled()
    yookassa_qr_enabled = is_yookassa_qr_configured()
    demo_enabled = is_demo_payment_enabled()

    if not crypto_configured and not stars_enabled and not cards_enabled and not yookassa_qr_enabled and not demo_enabled:
        error_title = 'Продление подписки' if key else 'Оплата'
        back_callback = f'key_renew:{key_id}' if key_id else 'buy_key'
        await safe_edit_or_send(
            message,
            f'💳 <b>{error_title}</b>\n\n😔 Способы оплаты временно недоступны.\nПопробуйте позже.',
            reply_markup=back_and_home_kb(back_callback=back_callback) if key else home_only_kb()
        )
        return None

    user_id = get_user_internal_id(telegram_id)
    prepared_order = None
    crypto_url = None

    if user_id:
        prepared_order = prepare_payment_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type=None,
            vpn_key_id=key_id,
            order_id=order_id,
        )
        order_id = prepared_order['order_id']


    # Баланс выведен из обращения (рефералка теперь начисляет дни, не баланс).
    show_balance_button = False

    discount_rub = (prepared_order or {}).get('discount_rub', 0) or 0
    auto_renew = bool((prepared_order or {}).get('auto_renew_requested'))
    recurring_available = get_setting('yookassa_recurring_enabled', '0') == '1'
    payment_text = _format_payment_context_text(
        tariff=tariff,
        key=key,
        discount_rub=discount_rub,
        intro_text=intro_text,
        auto_renew=auto_renew,
        recurring_available=recurring_available,
    )

    photo_file_id = None
    if key is None:
        payment_select_data = get_message_data('payment_select_text', '')
        photo_file_id = payment_select_data.get('photo_file_id')

    if key is None:
        kb = payment_method_kb(
            tariff_id=tariff_id,
            crypto_url=crypto_url,
            crypto_mode=crypto_mode,
            crypto_configured=crypto_configured,
            stars_enabled=stars_enabled,
            cards_enabled=cards_enabled,
            yookassa_qr_enabled=yookassa_qr_enabled,
            order_id=order_id,
            show_balance_button=show_balance_button,
            demo_enabled=demo_enabled,
            has_promocode=has_promocode or discount_rub > 0,
            auto_renew=auto_renew,
            recurring_available=recurring_available,
        )
    else:
        kb = renew_payment_method_kb(
            key_id=key_id,
            tariff_id=tariff_id,
            crypto_url=crypto_url,
            crypto_mode=crypto_mode,
            crypto_configured=crypto_configured,
            stars_enabled=stars_enabled,
            cards_enabled=cards_enabled,
            yookassa_qr_enabled=yookassa_qr_enabled,
            show_balance_button=show_balance_button,
            demo_enabled=demo_enabled,
            order_id=order_id,
            has_promocode=has_promocode or discount_rub > 0,
            auto_renew=auto_renew,
            recurring_available=recurring_available,
        )

    await safe_edit_or_send(message, payment_text, photo=photo_file_id, reply_markup=kb)
    return prepared_order
