"""
Роутер раздела «Оплаты».

Обрабатывает:
- Главный экран оплат
- Toggle для Stars/Crypto
- Настройка крипто-платежей
- Редактирование крипто-настроек
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, LinkPreviewOptions
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database.requests import (
    get_setting,
    set_setting,
    is_crypto_enabled,
    is_stars_enabled,
    is_cards_enabled,
    is_yookassa_qr_enabled,
    get_crypto_integration_mode,
    set_crypto_integration_mode,
    is_demo_payment_enabled
)
from bot.states.admin_states import (
    AdminStates,
    CRYPTO_PARAMS,
    get_crypto_param_by_index,
    get_total_crypto_params
)
from bot.utils.admin import is_admin
from bot.keyboards.admin import (
    payments_menu_kb,
    crypto_setup_kb,
    crypto_setup_confirm_kb,
    edit_crypto_kb,
    crypto_management_kb,
    cards_management_kb,
    back_and_home_kb
)
from bot.utils.text import escape_html, safe_edit_or_send

logger = logging.getLogger(__name__)


router = Router()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def has_crypto_data() -> bool:
    """Проверяет, заполнены ли данные крипто-платежей в БД."""
    url = get_setting('crypto_item_url', '')
    secret = get_setting('crypto_secret_key', '')
    return bool(url and secret)


def parse_item_id_from_url(url: str) -> str:
    """
    Извлекает item_id из ссылки на товар Ya.Seller.
    
    Формат: https://t.me/Ya_SellerBot?start=item-{item_id}...
    """
    try:
        if '?start=item-' in url:
            start_part = url.split('?start=item-')[1]
            # item_id — это первая часть до следующего дефиса или конца строки
            item_id = start_part.split('-')[0]
            return item_id
        elif '?start=item0-' in url:
            # Тестовый режим
            start_part = url.split('?start=item0-')[1]
            item_id = start_part.split('-')[0]
            return item_id
    except Exception:
        pass
    return ""


# ============================================================================
# ГЛАВНЫЙ ЭКРАН ОПЛАТ
# ============================================================================

@router.callback_query(F.data == "admin_payments")
async def show_payments_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает главный экран раздела оплат."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.payments_menu)

    stars = is_stars_enabled()
    crypto = is_crypto_enabled()
    cards = is_cards_enabled()
    qr = is_yookassa_qr_enabled()
    demo = is_demo_payment_enabled()

    text = (
        "💳 <b>Настройки оплаты</b>\n\n"
        "Здесь можно включить/выключить способы оплаты и настроить их.\n\n"
    )

    if stars:
        text += "🟢 <b>Telegram Stars</b>\n"
    else:
        text += "⚪ <b>Telegram Stars</b>\n"

    if crypto:
        item_url = get_setting('crypto_item_url', '')
        if item_url:
            text += f"🟢 <b>Крипто (@Ya_SellerBot)</b>\n<a href=\"{item_url}\">Ссылка на товар</a>\n"
        else:
            text += "🟢 <b>Крипто (@Ya_SellerBot)</b>\n"
    else:
        text += "⚪ <b>Крипто (@Ya_SellerBot)</b>\n"

    if cards:
        text += "🟢 <b>Оплата картами (ЮКасса Telegram Payments)</b>\n"
    else:
        text += "⚪ <b>Оплата картами (ЮКасса Telegram Payments)</b>\n"

    if qr:
        shop_id = get_setting('yookassa_shop_id', '')
        text += f"🟢 <b>QR-оплата (ЮКасса прямая/СБП)</b> | Shop ID: <code>{shop_id or '—'}</code>\n"
    else:
        text += "⚪ <b>QR-оплата (ЮКасса прямая/СБП)</b>\n"

    if demo:
        text += "🟢 <b>Демо оплата (РФ)</b>\n"
    else:
        text += "⚪ <b>Демо оплата (РФ)</b>\n"

    monthly_reset = get_setting('monthly_traffic_reset_enabled', '0') == '1'

    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=payments_menu_kb(stars, crypto, cards, qr, monthly_reset, demo)
    )
    await callback.answer()


# ============================================================================
# TOGGLE MONTHLY RESET
# ============================================================================

@router.callback_query(F.data == "admin_toggle_monthly_reset")
async def toggle_monthly_reset(callback: CallbackQuery, state: FSMContext):
    """Переключение автосброса трафика 1-го числа."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = get_setting('monthly_traffic_reset_enabled', '0')
    new_val = '0' if current == '1' else '1'
    set_setting('monthly_traffic_reset_enabled', new_val)
    
    # Перерисовываем меню оплат
    await show_payments_menu(callback, state)


# ============================================================================
# TOGGLE STARS
# ============================================================================

@router.callback_query(F.data == "admin_payments_toggle_stars")
async def toggle_stars(callback: CallbackQuery, state: FSMContext):
    """Переключает Telegram Stars."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = is_stars_enabled()
    new_value = '0' if current else '1'
    set_setting('stars_enabled', new_value)
    
    status = "включены ⭐" if new_value == '1' else "выключены"
    await callback.answer(f"Telegram Stars {status}")
    
    # Обновляем экран
    await show_payments_menu(callback, state)


# ============================================================================
# TOGGLE DEMO PAYMENT
# ============================================================================

@router.callback_query(F.data == "admin_payments_toggle_demo")
async def toggle_demo(callback: CallbackQuery, state: FSMContext):
    """Переключает демо оплату РФ картой."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = is_demo_payment_enabled()
    new_value = '0' if current else '1'
    set_setting('demo_payment_enabled', new_value)
    
    status = "включена" if new_value == '1' else "выключена"
    await callback.answer(f"Демо оплата {status}")
    
    # Обновляем экран
    await show_payments_menu(callback, state)


# ============================================================================
# TOGGLE CRYPTO
# ============================================================================

@router.callback_query(F.data == "admin_payments_toggle_crypto")
async def toggle_crypto(callback: CallbackQuery, state: FSMContext):
    """Открывает настройку или меню управления крипто-платежами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Проверяем, есть ли данные в БД
    if has_crypto_data():
        # Если данные есть → меню управления
        await show_crypto_management_menu(callback, state)
    else:
        # Если данных нет → диалог настройки
        await start_crypto_setup(callback, state)


# ============================================================================
# НАСТРОЙКА КРИПТО-ПЛАТЕЖЕЙ
# ============================================================================

async def start_crypto_setup(callback: CallbackQuery, state: FSMContext):
    """Начинает диалог настройки крипто-платежей."""
    await state.set_state(AdminStates.crypto_setup_url)
    await state.update_data(crypto_data={}, crypto_step=1)
    
    # Получаем username бота для инструкции
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else "YOUR_BOT"
    callback_url = f"https://t.me/{bot_username}"
    
    mode = get_crypto_integration_mode()
    
    instructions = (
        "<b>Режим «Простой» (рекомендуется):</b>\n"
        "1️⃣ В @Ya_SellerBot выберите «Управление» → «Товары» → «Добавить»\n"
        "2️⃣ Выберите тип позиции: <b>Счет</b>\n\n"
        "🎬 <b>Актуальная инструкция как добавлять:</b>\n"
        "<a href=\"https://youtu.be/cK0wX2LKxcs\">Смотреть видео</a>\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "• Тип позиции — именно <b>Счет</b>, а НЕ <b>Товар</b>!\n"
        "• Тарифы добавлять к позиции <b>НЕ нужно</b> — в режиме «Счет» их нельзя туда добавить.\n"
        "• Бот сам сформирует сумму оплаты на основе выбранного тарифа.\n\n"
    ) if mode == 'simple' else (
        "<b>Режим «Стандартный»:</b>\n"
        "1️⃣ Создайте обычный <b>Товар</b> в @Ya_SellerBot\n"
        "2️⃣ Добавьте в него тарифы (под номерами 1-9)\n"
        "3️⃣ Обязательно добавьте ID тарифов (1-9) из бота Ya.Seller в каждый тариф нашего VPN-бота.\n\n"
        "🎬 Процесс добавления товара показан в <a href=\"https://www.youtube.com/watch?v=MYRTzvIkbi0\">видео-инструкции</a>.\n\n"
    )

    text = (
        "💰 <b>Настройка крипто-платежей</b>\n\n"
        "Для приёма криптовалюты мы используем @Ya_SellerBot.\n\n"
        f"{instructions}"
        "🔗 *Теперь скопируйте ссылку на позицию из бота и отправьте её мне:*"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=crypto_setup_kb(1)
    )


@router.message(AdminStates.crypto_setup_url)
async def process_crypto_url(message: Message, state: FSMContext):
    """Обрабатывает ввод ссылки на товар."""
    from bot.utils.text import get_message_text_for_storage
    
    url = get_message_text_for_storage(message, 'plain')
    
    # Валидация
    param = get_crypto_param_by_index(0)
    if not param['validate'](url):
        await safe_edit_or_send(message,
            f"❌ {param['error']}\n\nПопробуйте ещё раз:"
        )
        return
    
    # Удаляем сообщение
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем режим
    data = await state.get_data()
    edit_mode = data.get('edit_mode', False)
    
    if edit_mode:
        # Режим редактирования - сохраняем и возвращаемся в меню
        set_setting('crypto_item_url', url)
        await state.update_data(edit_mode=False)
        
        await safe_edit_or_send(message,
            f"✅ Ссылка обновлена!\n<a href=\"{url}\">{escape_html(url)}</a>",
            force_new=True
        )
        
        # Создаём фейковый callback для показа меню
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.from_user = user
                self.bot = msg.bot
            async def answer(self, *args, **kwargs):
                pass
        
        fake = FakeCallback(message, message.from_user)
        await show_crypto_management_menu(fake, state)
    else:
        # Режим настройки - сохраняем во временные данные
        crypto_data = data.get('crypto_data', {})
        crypto_data['crypto_item_url'] = url
        await state.update_data(crypto_data=crypto_data, crypto_step=2)
        
        # Переходим к вводу секретного ключа
        await state.set_state(AdminStates.crypto_setup_secret)
        
        bot_username = message.bot.my_username if hasattr(message.bot, 'my_username') else "YOUR_BOT"
        callback_url = f"https://t.me/{bot_username}"

        await safe_edit_or_send(message,
            f"✅ Ссылка принята!\n<a href=\"{url}\">{escape_html(url)}</a>\n\n"
            "🔔 <b>Настройка уведомлений:</b>\n"
            "В @Ya_SellerBot зайдите в настройки вашей созданной позиции → <code>Уведомления</code> → <code>Обратная ссылка</code> и укажите этот адрес:\n"
            f"<code>{callback_url}</code>\n\n"
            "🔑 <b>Ожидаю ввода секретного ключа:</b>\n"
            "Найти его можно в @Ya_SellerBot: <code>Профиль</code> → <code>Ключ подписи</code>.",
            reply_markup=crypto_setup_kb(2),
            force_new=True
        )


@router.message(AdminStates.crypto_setup_secret)
async def process_crypto_secret(message: Message, state: FSMContext):
    """Обрабатывает ввод секретного ключа."""
    from bot.utils.text import get_message_text_for_storage
    
    secret = get_message_text_for_storage(message, 'plain')
    
    # Валидация
    param = get_crypto_param_by_index(1)
    if not param['validate'](secret):
        await safe_edit_or_send(message,
            f"❌ {param['error']}\n\nПопробуйте ещё раз:"
        )
        return
    
    # Удаляем сообщение (там секретный ключ!)
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем режим
    data = await state.get_data()
    edit_mode = data.get('edit_mode', False)
    
    if edit_mode:
        # Режим редактирования - сохраняем и возвращаемся в меню
        set_setting('crypto_secret_key', secret)
        await state.update_data(edit_mode=False)
        await safe_edit_or_send(message, "✅ Секретный ключ обновлён!", force_new=True)
        
        # Создаём фейковый callback для показа меню
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.from_user = user
                self.bot = msg.bot
            async def answer(self, *args, **kwargs):
                pass
        
        fake = FakeCallback(message, message.from_user)
        await show_crypto_management_menu(fake, state)
    else:
        # Режим настройки - сохраняем во временные данные
        crypto_data = data.get('crypto_data', {})
        crypto_data['crypto_secret_key'] = secret
        await state.update_data(crypto_data=crypto_data)
        
        # Переходим к подтверждению
        await state.set_state(AdminStates.payments_menu)
        
        item_url = crypto_data.get('crypto_item_url', '')
        
        await safe_edit_or_send(message,
            "✅ <b>Все данные введены!</b>\n\n"
            f"📦 Товар: <a href=\"{item_url}\">{escape_html(item_url)}</a>\n"
            f"🔐 Ключ: <code>{'•' * 16}</code>\n\n"
            "Сохранить и включить крипто-платежи?",
            reply_markup=crypto_setup_confirm_kb(),
            force_new=True
        )


@router.callback_query(F.data == "admin_crypto_setup_back")
async def crypto_setup_back(callback: CallbackQuery, state: FSMContext):
    """Возврат на предыдущий шаг настройки крипто."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    step = data.get('crypto_step', 1)
    
    if step <= 1:
        # Возврат к меню оплат
        await show_payments_menu(callback, state)
    else:
        # Возврат к вводу URL
        await state.set_state(AdminStates.crypto_setup_url)
        await state.update_data(crypto_step=1)
        await start_crypto_setup(callback, state)
    
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_setup_save")
async def crypto_setup_save(callback: CallbackQuery, state: FSMContext):
    """Сохраняет настройки крипто и включает их."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    crypto_data = data.get('crypto_data', {})
    
    if not crypto_data.get('crypto_item_url') or not crypto_data.get('crypto_secret_key'):
        await callback.answer("❌ Данные не полные", show_alert=True)
        return
    
    # Сохраняем
    set_setting('crypto_item_url', crypto_data['crypto_item_url'])
    set_setting('crypto_secret_key', crypto_data['crypto_secret_key'])
    set_setting('crypto_enabled', '1')
    
    await callback.answer("✅ Крипто-платежи включены!")
    
    await safe_edit_or_send(callback.message, 
        "✅ <b>Крипто-платежи настроены и включены!</b>\n\n"
        "Теперь пользователи смогут оплачивать криптовалютой.\n"
        "Не забудьте добавить тарифы с указанием ID тарифа (1-9)!"
    )
    
    # Показываем меню оплат
    await show_payments_menu(callback, state)


# ============================================================================
# МЕНЮ УПРАВЛЕНИЯ КРИПТО-ПЛАТЕЖАМИ
# ============================================================================

async def show_crypto_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления крипто-платежами."""
    await state.set_state(AdminStates.payments_menu)
    
    is_enabled = is_crypto_enabled()
    item_url = get_setting('crypto_item_url', '')
    mode = get_crypto_integration_mode()
    
    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включены" if is_enabled else "выключены"
    
    mode_title = "Простой (Счет)" if mode == 'simple' else "Стандартный (Товар)"
    
    mode_description = (
        "ℹ️ <b>В Простом (Счет) режиме</b> бот генерирует ссылку на оплату с указанием точной суммы в долларах (из настроек тарифа).\n\n"
        "⚠️ <b>ВАЖНО:</b> В Ya.Seller позиция обязательно должна иметь тип <b>«Счет»</b>, а НЕ <b>«Товар»</b>! Тарифы к позиции добавлять не нужно — бот сам указывает сумму. Настраивать ID тарифов (external_id) не требуется.\n\n"
    ) if mode == 'simple' else (
        "ℹ️ <b>В Стандартном режиме</b> бот отправляет покупателя на одну ссылку-товар, где он выбирает тариф. Вам нужно обязательно заполнить поле «ID тарифа из Ya.Seller» для каждого тарифа.\n\n"
    )
    
    if item_url:
        safe_url = escape_html(item_url)
        text = (
            "💰 <b>Управление крипто-платежами</b>\n\n"
            f"{status_emoji} Статус: <b>{status_text}</b>\n"
            f"📦 Ссылка/Товар: <a href=\"{item_url}\">{safe_url}</a>\n"
            f"⚙️ Текущий режим: <b>{mode_title}</b>\n\n"
            f"{mode_description}"
            "Выберите действие:"
        )
    else:
        text = (
            "💰 <b>Управление крипто-платежами</b>\n\n"
            f"{status_emoji} Статус: <b>{status_text}</b>\n"
            "📦 Ссылка/Товар: —\n"
            f"⚙️ Текущий режим: <b>{mode_title}</b>\n\n"
            f"{mode_description}"
            "Выберите действие:"
        )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=crypto_management_kb(is_enabled, mode)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_mgmt_toggle_mode")
async def crypto_mgmt_toggle_mode(callback: CallbackQuery, state: FSMContext):
    """Переключает режим интеграции с криптой (simple/standard)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current_mode = get_crypto_integration_mode()
    new_mode = 'standard' if current_mode == 'simple' else 'simple'
    set_crypto_integration_mode(new_mode)
    
    await callback.answer(f"Режим переключен на: {new_mode}")
    # Обновляем меню
    await show_crypto_management_menu(callback, state)


@router.callback_query(F.data == "admin_crypto_mgmt_toggle")
async def crypto_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает крипто-платежи (без потери данных)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = is_crypto_enabled()
    new_value = '0' if current else '1'
    set_setting('crypto_enabled', new_value)
    
    status = "включены ✅" if new_value == '1' else "выключены"
    await callback.answer(f"Крипто-платежи {status}")
    
    # Обновляем меню
    await show_crypto_management_menu(callback, state)


@router.callback_query(F.data == "admin_crypto_mgmt_edit_url")
async def crypto_mgmt_edit_url(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование ссылки на товар."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.crypto_setup_url)
    await state.update_data(edit_mode=True)
    
    current_url = get_setting('crypto_item_url', '')
    
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else "YOUR_BOT"
    callback_url = f"https://t.me/{bot_username}"
    mode = get_crypto_integration_mode()
    
    instructions = (
        "<b>Режим «Простой» (Счет):</b>\n"
        "1️⃣ В @Ya_SellerBot выберите «Управление» → «Товары» → «Добавить»\n"
        "2️⃣ Выберите тип позиции: <b>Счет</b>\n\n"
        "🎬 <b>Актуальная инструкция как добавлять:</b>\n"
        "<a href=\"https://youtu.be/cK0wX2LKxcs\">Смотреть видео</a>\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "• Тип позиции — именно <b>Счет</b>, а НЕ <b>Товар</b>!\n"
        "• Тарифы добавлять к позиции <b>НЕ нужно</b> — в режиме «Счет» их нельзя туда добавить.\n"
        "• Бот сам сформирует сумму оплаты на основе выбранного тарифа.\n\n"
    ) if mode == 'simple' else (
        "<b>Режим «Стандартный» (Товар):</b>\n"
        "1️⃣ Создайте обычный <b>Товар</b> в @Ya_SellerBot\n"
        "2️⃣ Добавьте в него тарифы (под номерами 1-9)\n"
        "3️⃣ Обязательно добавьте ID тарифов (1-9) из бота Ya.Seller в каждый тариф нашего VPN-бота.\n\n"
        "🎬 Процесс добавления товара показан в <a href=\"https://www.youtube.com/watch?v=MYRTzvIkbi0\">видео-инструкции</a>.\n\n"
    )
    
    if current_url:
        safe_url = escape_html(current_url)
        text = (
            "🔗 <b>Изменение ссылки</b>\n\n"
            f"{instructions}"
            f"Текущая ссылка: <a href=\"{current_url}\">{safe_url}</a>\n\n"
            "🔗 <b>Введите новую ссылку из @Ya_SellerBot:</b>"
        )
    else:
        text = (
            "🔗 <b>Изменение ссылки</b>\n\n"
            f"{instructions}"
            "Текущая ссылка: —\n\n"
            "🔗 <b>Введите новую ссылку из @Ya_SellerBot:</b>"
        )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=back_and_home_kb("admin_crypto_management")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_mgmt_edit_secret")
async def crypto_mgmt_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование секретного ключа."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.crypto_setup_secret)
    await state.update_data(edit_mode=True)
    
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else "YOUR_BOT"
    callback_url = f"https://t.me/{bot_username}"

    text = (
        "🔐 <b>Изменение секретного ключа</b>\n\n"
        "🔔 <b>Настройка уведомлений:</b>\n"
        "В @Ya_SellerBot зайдите в настройки вашей созданной позиции → <code>Уведомления</code> → <code>Обратная ссылка</code> и укажите этот адрес:\n"
        f"<code>{callback_url}</code>\n\n"
        "🔑 <b>Ожидаю ввода нового секретного ключа:</b>\n"
        "Найти его можно в @Ya_SellerBot: <code>Профиль</code> → <code>Ключ подписи</code>."
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=back_and_home_kb("admin_crypto_management")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_management")
async def back_to_crypto_management(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню управления крипто-платежами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await show_crypto_management_menu(callback, state)


# ============================================================================
# РЕДАКТИРОВАНИЕ КРИПТО-НАСТРОЕК
# ============================================================================

@router.callback_query(F.data == "admin_payments_crypto_settings")
async def start_edit_crypto(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.edit_crypto)
    await state.update_data(edit_crypto_param=0)
    
    await show_crypto_edit_screen(callback, state, 0)


async def show_crypto_edit_screen(callback: CallbackQuery, state: FSMContext, param_index: int):
    """Показывает экран редактирования крипто-настройки."""
    param = get_crypto_param_by_index(param_index)
    total = get_total_crypto_params()
    
    current_value = get_setting(param['key'], '')
    
    # Маскируем секретный ключ
    if param['key'] == 'crypto_secret_key' and current_value:
        display_value = '•' * min(len(current_value), 16)
    else:
        display_value = current_value or '—'
    
    text = (
        f"⚙️ <b>Настройки крипто-платежей</b> ({param_index + 1}/{total})\n\n"
        f"📌 Параметр: <b>{param['label']}</b>\n"
        f"📝 Текущее значение: <code>{display_value}</code>\n\n"
        f"Введите новое значение или используйте кнопки навигации:\n"
        f"({param['hint']})"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=edit_crypto_kb(param_index, total)
    )


@router.callback_query(F.data == "admin_crypto_edit_prev")
async def crypto_edit_prev(callback: CallbackQuery, state: FSMContext):
    """Предыдущий параметр крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    current = data.get('edit_crypto_param', 0)
    new_param = max(0, current - 1)
    await state.update_data(edit_crypto_param=new_param)
    
    await show_crypto_edit_screen(callback, state, new_param)
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_edit_next")
async def crypto_edit_next(callback: CallbackQuery, state: FSMContext):
    """Следующий параметр крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    current = data.get('edit_crypto_param', 0)
    total = get_total_crypto_params()
    new_param = min(total - 1, current + 1)
    await state.update_data(edit_crypto_param=new_param)
    
    await show_crypto_edit_screen(callback, state, new_param)
    await callback.answer()


@router.message(AdminStates.edit_crypto)
async def edit_crypto_value(message: Message, state: FSMContext):
    """Обрабатывает ввод нового значения крипто-настройки."""
    if not is_admin(message.from_user.id):
        return
    
    from bot.utils.text import get_message_text_for_storage
    
    data = await state.get_data()
    param_index = data.get('edit_crypto_param', 0)
    
    param = get_crypto_param_by_index(param_index)
    value = get_message_text_for_storage(message, 'plain')
    
    # Валидация
    if not param['validate'](value):
        await safe_edit_or_send(message,
            f"❌ {param['error']}"
        )
        return
    
    # Сохраняем в БД
    set_setting(param['key'], value)
    
    # Удаляем сообщение
    try:
        await message.delete()
    except:
        pass
    
    # Показываем обновлённый экран
    await safe_edit_or_send(message,
        f"✅ <b>{param['label']}</b> обновлено!",
        force_new=True
    )
    
    # Создаём фейковый callback для показа экрана
    # Это хак, но работает
    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        
        async def answer(self, *args, **kwargs):
            pass
    
    fake = FakeCallback(message, message.from_user)
    await show_crypto_edit_screen(fake, state, param_index)


@router.callback_query(F.data == "admin_crypto_edit_done")
async def crypto_edit_done(callback: CallbackQuery, state: FSMContext):
    """Завершение редактирования крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await callback.answer("✅ Настройки сохранены")
    await show_payments_menu(callback, state)


# ============================================================================
# УПРАВЛЕНИЕ ОПЛАТОЙ КАРТАМИ
# ============================================================================

@router.callback_query(F.data == "admin_payments_cards")
async def show_cards_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления оплатой картами (ЮКасса)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)
    
    is_enabled = is_cards_enabled()
    token = get_setting('cards_provider_token', '')
    
    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"
    
    if token:
        # Маскируем токен: первые 4 и последние 4 символа
        masked_token = f"{token[:4]}...{token[-4:]}"
        token_display = f"Установлен ✅ (<code>{masked_token}</code>)"
    else:
        token_display = "Не установлен ❌"
    
    text = (
        "💳 <b>Управление оплатой картами</b>\n\n"
        "Для работы этого способа необходимо настроить провайдера ЮКасса.\n\n"
        "❗️ <b>ШАГ 1: РЕГИСТРАЦИЯ</b>\n"
        "Обязательно <a href=\"https://yookassa.ru/joinups/?source=sva\">зарегистрируйте магазин в ЮКассе по этой ссылке</a>\n\n"
        "После проверки документов ЮКассой переходите к настройке токена.\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🔑 Provider Token: <b>{token_display}</b>\n\n"
        "Выберите действие:"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=cards_management_kb(is_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_cards_mgmt_toggle")
async def cards_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает оплату картами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Нельзя включить, если нет токена
    if not is_cards_enabled() and not get_setting('cards_provider_token', ''):
        await callback.answer("❌ Сначала укажите Provider Token!", show_alert=True)
        return

    current = is_cards_enabled()
    new_value = '0' if current else '1'
    set_setting('cards_enabled', new_value)
    
    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"Оплата картами {status}")
    
    # Обновляем меню
    await show_cards_management_menu(callback, state)


@router.callback_query(F.data == "admin_cards_mgmt_edit_token")
async def cards_mgmt_edit_token(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование токена ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.cards_setup_token)
    # Сохраняем ID сообщения, чтобы потом его отредактировать
    await state.update_data(last_menu_msg_id=callback.message.message_id)
    
    text = (
        "🔗 <b>Установка Provider Token</b>\n\n"
        "❗️ <b>ШАГ 1: РЕГИСТРАЦИЯ В ЮКАССЕ</b>\n"
        "Обязательно <a href=\"https://yookassa.ru/joinups/?source=sva\">зарегистрируйтесь по этой ссылке</a>\n\n"
        "<b>ШАГ 2: ПОЛУЧЕНИЕ ТОКЕНА В @BotFather</b>\n"
        "1. Отправьте команду <code>/mybots</code> и выберите бота.\n"
        "2. Нажмите <code>Payments</code> → <code>YooKassa</code>.\n"
        "3. Подключите магазин в боте провайдера и **обязательно вернитесь в @BotFather**.\n"
        "4. В BotFather снова откройте <code>Payments</code>, там появится токен.\n\n"
        "Отправьте полученный токен ответом на это сообщение:"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=back_and_home_kb("admin_payments_cards")
    )
    await callback.answer()


@router.message(AdminStates.cards_setup_token)
async def cards_setup_token_value(message: Message, state: FSMContext):
    """Обрабатывает ввод токена ЮКасса."""
    from bot.utils.text import get_message_text_for_storage
    
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    token = get_message_text_for_storage(message, 'plain')
    
    if len(token) < 20 or ':' not in token:
        await safe_edit_or_send(message, "❌ Неверный формат токена. Попробуйте ещё раз:")
        return
    
    set_setting('cards_provider_token', token)
    
    try:
        await message.delete()
    except:
        pass
    
    # Если у нас есть ID сообщения меню, используем его для редактирования
    menu_message = message
    if last_menu_msg_id:
        try:
            # Создаем объект сообщения с нужным ID для редактирования
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛ Сохранение..."
            )
        except Exception:
            # Если не вышло (например, сообщение удалено), будем отвечать новым
            menu_message = await safe_edit_or_send(message, "⌛ Сохранение...", force_new=True)

    # Возвращаемся в меню через FakeCallback
    class FakeCallback:
        def __init__(self, msg, user, success_msg=None):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
            self.data = "admin_payments_cards"
            self.success_msg = success_msg
        
        async def answer(self, text=None, show_alert=False, *args, **kwargs):
            # Если передали текст для popup, запоминаем его (он будет показан при нажатии кнопок)
            # Но так как в AIOGram answerCallbackQuery работает только для реальных инстансов,
            # мы просто выведем информацию в консоль или пропустим.
            # Для пользователя мы добавим текст в само сообщение.
            pass

    fake = FakeCallback(menu_message, message.from_user)
    await show_cards_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА QR-ОПЛАТЫ ЮКАССА (прямой API)
# ============================================================================

def qr_management_kb(is_enabled: bool) -> "InlineKeyboardMarkup":
    """Клавиатура управления QR-оплатой ЮКасса."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from bot.keyboards.admin import back_button, home_button

    builder = InlineKeyboardBuilder()

    toggle_text = "🔴 Выключить" if is_enabled else "🟢 Включить"
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data="admin_qr_mgmt_toggle"))
    builder.row(InlineKeyboardButton(text="🏪 Изменить Shop ID", callback_data="admin_qr_edit_shop_id"))
    builder.row(InlineKeyboardButton(text="🔐 Изменить Secret Key", callback_data="admin_qr_edit_secret"))
    builder.row(back_button("admin_payments"), home_button())

    return builder.as_markup()


@router.callback_query(F.data == "admin_payments_qr")
async def show_qr_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления QR-оплатой ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    from database.requests import is_yookassa_qr_enabled
    is_enabled = is_yookassa_qr_enabled()
    shop_id = get_setting('yookassa_shop_id', '')
    secret_key = get_setting('yookassa_secret_key', '')

    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"

    shop_display = f"<code>{shop_id}</code>" if shop_id else "❌ Не задан"
    secret_display = f"Установлен ✅ (<code>{secret_key[:4]}...{secret_key[-4:]}</code>)" if len(secret_key) >= 8 else "❌ Не задан"

    text = (
        "📱 <b>QR-оплата ЮКасса (прямой API)</b>\n\n"
        "Позволяет принимать оплату картами и через СБП по QR-коду,\n"
        "без Telegram Payments.\n\n"
        "📋 <b>Как получить доступ:</b>\n"
        "1. Зарегистрируйте магазин: <a href=\"https://yookassa.ru/joinups/?source=sva\">yookassa.ru</a>\n"
        "2. Перейдите: Настройки → API-интеграция\n"
        "3. Скопируйте Shop ID и сгенерируйте новый Secret Key\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🏪 Shop ID: {shop_display}\n"
        f"🔑 Secret Key: {secret_display}\n\n"
        "Выберите действие:"
    )

    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=qr_management_kb(is_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_qr_mgmt_toggle")
async def qr_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает QR-оплату ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    from database.requests import is_yookassa_qr_enabled

    # Нельзя включить без реквизитов
    if not is_yookassa_qr_enabled():
        shop_id = get_setting('yookassa_shop_id', '')
        secret_key = get_setting('yookassa_secret_key', '')
        if not shop_id or not secret_key:
            await callback.answer("❌ Сначала укажите Shop ID и Secret Key!", show_alert=True)
            return

    current = is_yookassa_qr_enabled()
    new_value = '0' if current else '1'
    set_setting('yookassa_qr_enabled', new_value)

    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"QR-оплата {status}")
    await show_qr_management_menu(callback, state)


@router.callback_query(F.data == "admin_qr_edit_shop_id")
async def qr_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Shop ID ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.qr_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    current = get_setting('yookassa_shop_id', '')
    current_display = f"\nТекущий: <code>{current}</code>" if current else ""

    await safe_edit_or_send(callback.message, 
        f"🏪 <b>Введите Shop ID ЮКасса</b>{current_display}\n\n"
        "Найдите в разделе: <b>Настройки → API-интеграция</b> вашего магазина.\n"
        "(Это числовой ID, например: <code>123456</code>)",
        reply_markup=back_and_home_kb("admin_payments_qr")
    )
    await callback.answer()


@router.message(AdminStates.qr_setup_shop_id)
async def qr_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Shop ID."""
    from bot.utils.text import get_message_text_for_storage
    
    shop_id = get_message_text_for_storage(message, 'plain')

    if not shop_id.isdigit() or len(shop_id) < 3:
        await safe_edit_or_send(message, "❌ Некорректный Shop ID. Должен быть числом (например, <code>123456</code>).")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('yookassa_shop_id', shop_id)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_qr_management_menu(fake, state)



@router.callback_query(F.data == "admin_qr_edit_secret")
async def qr_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Secret Key ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.qr_setup_secret_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(callback.message, 
        "🔐 <b>Введите Secret Key ЮКасса</b>\n\n"
        "Найдите в разделе: <b>Настройки → API-интеграция</b> вашего магазина.\n"
        "_(Секретный ключ будет скрыт после сохранения)_",
        reply_markup=back_and_home_kb("admin_payments_qr")
    )
    await callback.answer()


@router.message(AdminStates.qr_setup_secret_key)
async def qr_setup_secret_key_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Secret Key."""
    from bot.utils.text import get_message_text_for_storage
    
    secret_key = get_message_text_for_storage(message, 'plain')

    if len(secret_key) < 16:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('yookassa_secret_key', secret_key)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_qr_management_menu(fake, state)


