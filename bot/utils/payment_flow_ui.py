from datetime import datetime
from typing import Optional, Dict, Any

from bot.utils.text import escape_html, safe_edit_or_send


def _pluralize_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} день"
    if n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return f"{n} дня"
    return f"{n} дней"


def _format_payment_context_text(
    tariff: Dict[str, Any],
    key: Optional[Dict[str, Any]] = None,
    discount_rub: int = 0,
    intro_text: Optional[str] = None,
) -> str:
    is_renew = key is not None
    title = "💳 <b>Продление подписки</b>" if is_renew else "💳 <b>Оплата подписки</b>"
    header_lines = [title]

    if is_renew:
        header_lines.append(f"🔑 <b>Подписка:</b> {escape_html(key['display_name'])}")

    traffic_gb = tariff.get('traffic_limit_gb', 0) or 0
    traffic_text = f"{traffic_gb} ГБ" if traffic_gb > 0 else "Безлимит"

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

    duration_label = "Продление" if is_renew else "Срок"
    block_lines = [
        f"Тариф: {escape_html(tariff['name'])}",
        f"Стоимость: {price_text}",
        f"{duration_label}: {tariff['duration_days']} дней",
        f"Трафик: {traffic_text}",
    ]

    if discount_rub > 0 and tariff.get('price_rub'):
        block_lines.append(f"Скидка по промокоду: {discount_rub} ₽")

    text = "\n\n".join(header_lines + [f"<blockquote>{chr(10).join(block_lines)}</blockquote>", "Выберите способ оплаты:"])
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
        custom_text = tariff_select_data.get('text', '').strip()
        photo_file_id = tariff_select_data.get('photo_file_id')
        text = custom_text or '💳 <b>Купить подписку</b>\n\nВыберите тариф:'

        await safe_edit_or_send(
            message,
            text,
            photo=photo_file_id,
            reply_markup=tariff_select_kb(tariffs, back_callback='start', order_id=order_id, is_select_only=True)
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
        f"💳 <b>Продление подписки</b>\n\n"
        f"🔑 <b>Подписка:</b> {escape_html(key['display_name'])}\n"
        f"📅 <b>Действует до:</b> {expires}\n"
        f"⏳ <b>Осталось:</b> {days_text}\n\n"
        f"Выберите тариф:"
    )

    await safe_edit_or_send(
        message,
        text,
        reply_markup=tariff_select_kb(
            tariffs,
            back_callback=f'key:{key_id}',
            order_id=order_id,
            is_select_only=True,
            select_callback_prefix='key_renew_tariff',
            select_callback_suffix=f':{key_id}',
        )
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
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    from bot.utils.message_editor import get_message_data
    from database.requests import (
        get_key_details_for_user, get_setting, get_tariff_by_id, get_user_balance,
        get_user_internal_id, get_crypto_integration_mode, is_cards_enabled,
        is_crypto_configured, is_demo_payment_enabled, is_referral_enabled,
        is_stars_enabled, is_yookassa_qr_configured, get_referral_reward_type,
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

    crypto_configured = is_crypto_configured()
    crypto_mode = get_crypto_integration_mode()
    stars_enabled = is_stars_enabled()
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

        if crypto_configured and crypto_mode == 'standard':
            crypto_item_url = get_setting('crypto_item_url')
            item_id = extract_item_id_from_url(crypto_item_url)
            if item_id:
                crypto_url = build_crypto_payment_url(
                    item_id=item_id,
                    invoice_id=order_id,
                    tariff_external_id=tariff.get('external_id'),
                    price_cents=tariff['price_cents']
                )

    # Баланс выведен из обращения (рефералка теперь начисляет дни, не баланс).
    show_balance_button = False

    discount_rub = (prepared_order or {}).get('discount_rub', 0) or 0
    payment_text = _format_payment_context_text(
        tariff=tariff,
        key=key,
        discount_rub=discount_rub,
        intro_text=intro_text,
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
        )

    await safe_edit_or_send(message, payment_text, photo=photo_file_id, reply_markup=kb)
    return prepared_order
