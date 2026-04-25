"""
Утилита для отправки VPN-ключей пользователю.
"""
import logging
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.vpn_api import get_client
from bot.utils.key_generator import generate_link, generate_json, generate_qr_code
from bot.utils.subscription import get_subscription_url, format_subscription_message
from database.requests import get_user_keys_for_display

logger = logging.getLogger(__name__)


# Дефолтный текст выдачи ключа в формате HTML
DEFAULT_KEY_DELIVERY_TEXT = (
    "✅ <b>Ваш VPN-ключ!</b>\n\n"
    "%ключ%\n"
    "☝️ Нажмите, чтобы скопировать.\n\n"
    "📱 <b>Инструкция:</b>\n"
    "1. Скопируйте ссылку или отсканируйте QR-код.\n"
    "2. Импортируйте в свой клиент. Какой именно клиент подходит, смотри в инструкции по кнопке ниже.\n"
    "3. Нажмите подключиться!"
)


async def send_key_with_qr(
    messageable, 
    key_data: dict, 
    key_manage_markup: InlineKeyboardMarkup = None,
    is_new: bool = False
):
    """
    Отправляет пользователю ключ с QR-кодом и файлом конфигурации.
    
    Использует единый HTML-контракт для текстов из редактора.
    
    Args:
        messageable: Объект Message или CallbackQuery, куда отвечать
        key_data: Данные ключа из БД (должны содержать server_id, panel_email, client_uuid)
        key_manage_markup: Клавиатура управления ключом
        is_new: Является ли ключ только что созданным
    """
    from bot.utils.text import escape_html
    
    try:
        # Проверяем наличие необходимых данных
        if not key_data.get('server_id') or not key_data.get('panel_email'):
             await _send_error(messageable, "Неполные данные ключа", key_manage_markup)
             return

        # 1. Получаем конфигурацию с сервера
        try:
            client = await get_client(key_data['server_id'])
            config = await client.get_client_config(key_data['panel_email'])
        except Exception as e:
            logger.error(f"Failed to get client config: {e}")
            config = None
            
        if not config:
            # Если не удалось получить конфиг (например, сервер недоступен),
            # отправляем просто UUID (как раньше)
            uuid = key_data.get('client_uuid', 'Unknown')
            text = (
                f"📋 <b>Ваш VPN-ключ</b>\n\n"
                f"<pre>{escape_html(uuid)}</pre>\n\n"
                "☝️ Нажмите на ключ, чтобы скопировать.\n"
                "⚠️ Не удалось получить полную конфигурацию (сервер недоступен).\n"
                "Попробуйте позже."
            )
            await _send_text(messageable, text, key_manage_markup)
            return

        # 2. Генерируем данные
        logger.info(f"Generating key for {key_data.get('panel_email')} (protocol: {config.get('protocol', 'vless')})")
        link = generate_link(config)
            
        json_config = generate_json(config)
        qr_bytes = generate_qr_code(link)
        
        # 3. Формируем сообщение через единый helper
        from bot.utils.message_editor import get_message_data
        
        delivery_data = get_message_data('key_delivery_text', DEFAULT_KEY_DELIVERY_TEXT)
        base_caption = delivery_data.get('text', DEFAULT_KEY_DELIVERY_TEXT)
        
        # Подстановка %ключ% — внутри <pre> экранирование не нужно
        key_snippet = f"<pre>{link}</pre>"
        caption = base_caption.replace('%ключ%', key_snippet)
        
        # Если caption слишком длинный (Telegram limit 1024), сокращаем
        if len(caption) > 1024:
             title = "✅ <b>Ваш новый VPN-ключ!</b>" if is_new else "📋 <b>Ваш VPN-ключ</b>"
             caption = (
                f"{title}\n\n"
                "👇 <b>Ваша ссылка доступа (нажмите для копирования):</b>\n"
                f"<code>{escape_html(link)}</code>\n\n"
                "📸 Отсканируйте QR-код для быстрого подключения."
             )

        # 4. Отправляем фото с QR и ссылкой
        photo = BufferedInputFile(qr_bytes, filename="qrcode.png")
        
        # Определяем функцию отправки
        send_func = messageable.answer_photo if hasattr(messageable, 'answer_photo') else messageable.message.answer_photo
        
        # Отправляем QR с ключом и клавиатурой
        await send_func(
            photo=photo,
            caption=caption,
            reply_markup=key_manage_markup,
            parse_mode="HTML"
        )
        
        # Удаляем старое сообщение если это callback
        if hasattr(messageable, 'message'):
            try:
                await messageable.message.delete()
            except:
                pass

    except Exception as e:
        logger.error(f"Error sending key: {e}")
        await _send_error(messageable, f"Ошибка отправки ключа: {e}", key_manage_markup)


async def _send_error(messageable, text, markup):
    """Отправляет сообщение об ошибке."""
    from bot.utils.text import safe_edit_or_send
    msg_text = f"❌ {text}"
    # Определяем Message для safe_edit_or_send
    if hasattr(messageable, 'text') or hasattr(messageable, 'photo'):
        # Это Message
        await safe_edit_or_send(messageable, msg_text, reply_markup=markup)
    elif hasattr(messageable, 'message'):
        # Это CallbackQuery
        await safe_edit_or_send(messageable.message, msg_text, reply_markup=markup)
    else:
        func = messageable.answer if hasattr(messageable, 'answer') else messageable.message.answer
        await func(msg_text, reply_markup=markup)


async def _send_text(messageable, text, markup):
    """Отправляет текстовое сообщение (fallback при отсутствии фото). HTML."""
    from bot.utils.text import safe_edit_or_send
    if hasattr(messageable, 'text') or hasattr(messageable, 'photo'):
        await safe_edit_or_send(messageable, text, reply_markup=markup)
    elif hasattr(messageable, 'message'):
        await safe_edit_or_send(messageable.message, text, reply_markup=markup)
    else:
        func = messageable.answer if hasattr(messageable, 'answer') else messageable.message.answer
        await func(text, reply_markup=markup, parse_mode="HTML")


async def send_subscription_link(
    messageable,
    key_id: int,
    key_manage_markup: InlineKeyboardMarkup = None
):
    """
    Отправляет пользователю subscription ссылку для конкретного ключа с QR-кодом.
    
    Args:
        messageable: Объект Message или CallbackQuery
        key_id: ID ключа из vpn_keys
        key_manage_markup: Клавиатура управления (опционально)
    """
    from bot.utils.text import safe_edit_or_send
    from bot.utils.key_generator import generate_qr_code
    from aiogram.types import BufferedInputFile
    from bot.keyboards.user import InlineKeyboardBuilder, InlineKeyboardButton
    from database.requests import get_vpn_key_by_id
    
    try:
        # Получаем данные ключа
        key = get_vpn_key_by_id(key_id)
        if not key:
            await _send_error(messageable, "Ключ не найден", key_manage_markup)
            return
        
        sub_id = key.get('sub_id')
        if not sub_id:
            await _send_error(messageable, "У ключа нет subscription ID", key_manage_markup)
            return
        
        # Получаем subscription URL для конкретного ключа
        from config import SUBSCRIPTION_URL
        sub_url = f"{SUBSCRIPTION_URL}/sub/{sub_id}"
        
        # Генерируем QR-код
        qr_bytes = generate_qr_code(sub_url)
        qr_file = BufferedInputFile(qr_bytes, filename="subscription_qr.png")
        
        # Формируем сообщение
        message_text = (
            "🔗 <b>Ваша подписка</b>\n\n"
            f"<pre>{sub_url}</pre>\n\n"
            "☝️ Нажмите на ссылку, чтобы скопировать.\n\n"
            "📱 <b>Инструкция по подключению:</b>"
        )
        
        # Создаем клавиатуру если не передана
        if not key_manage_markup:
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📄 Инструкция", callback_data="device_instructions"))
            builder.row(
                InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys"),
                InlineKeyboardButton(text="🏠 На главную", callback_data="start")
            )
            key_manage_markup = builder.as_markup()
        
        # Отправляем фото с QR-кодом
        if hasattr(messageable, 'message'):
            # Это CallbackQuery
            try:
                await messageable.message.delete()
            except Exception:
                pass
            await messageable.message.answer_photo(
                photo=qr_file,
                caption=message_text,
                reply_markup=key_manage_markup,
                parse_mode="HTML"
            )
        else:
            # Это Message
            await messageable.answer_photo(
                photo=qr_file,
                caption=message_text,
                reply_markup=key_manage_markup,
                parse_mode="HTML"
            )
            
        logger.info(f"Отправлена subscription ссылка для ключа {key_id} (sub_id={sub_id})")
        
    except Exception as e:
        logger.error(f"Ошибка отправки subscription ссылки: {e}")
        await _send_error(messageable, f"Ошибка: {e}", key_manage_markup)
