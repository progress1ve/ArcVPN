from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAnimation, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest
from typing import Literal, Optional, Union
import logging

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """Экранирование спецсимволов для HTML parse_mode."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_message_text_for_storage(
    message: Message,
    text_type: Literal['html', 'plain'] = 'html'
) -> str:
    """Извлекает текст из сообщения для сохранения в БД.
    
    Поддерживает как обычные текстовые сообщения (html_text/text),
    так и медиа-сообщения (html_caption/caption).
    
    Args:
        text_type: 'html' — тексты с форматированием (использует html_text/html_caption),
                   'plain' — технические значения (URL, секреты, числа).
    """
    if text_type == 'html':
        # html_text сохраняет форматирование пользователя в HTML-тегах
        if message.html_text:
            return message.html_text.strip()
        if message.text:
            return message.text.strip()
        if hasattr(message, 'html_caption') and message.html_caption:
            return message.html_caption.strip()
        if message.caption:
            return message.caption.strip()
        return ""
    else:  # plain
        if message.text:
            return message.text.strip()
        if message.caption:
            return message.caption.strip()
        return ""


async def safe_edit_or_send(
    message: Message,
    text: str = None,
    reply_markup=None,
    photo: Optional[Union[str, object]] = None,
    show_web_page_preview: bool = False,
    force_new: bool = False,
) -> Message:
    """Универсальная функция редактирования/отправки сообщения.
    
    parse_mode='HTML' зашит внутри — вызывающий код не может передать другой режим.
    
    Автоматически определяет тип текущего сообщения и целевой формат,
    выбирая оптимальную стратегию:
    
    - текст → текст: edit_text
    - медиа → текст: удалить + answer (текст)
    - текст → медиа: удалить + answer_photo
    - медиа → медиа: edit_media + edit_caption
    
    Обрабатывает ошибки Telegram API:
    - 'there is no text in the message to edit'
    - 'message is not modified'
    
    Args:
        message: Сообщение для редактирования
        text: Текст сообщения (или caption для медиа)
        reply_markup: Клавиатура
        photo: Фото (file_id, URL или InputFile). Если передано — отправляем медиа-сообщение
    """
    is_current_media = bool(message.photo or message.video or message.document or message.animation)
    want_media = photo is not None
    
    # Отключаем превью ссылок по умолчанию. Включаем только если show_web_page_preview=True
    link_preview = LinkPreviewOptions(is_disabled=not show_web_page_preview)
    
    # Если requested force_new, просто отправляем новое сообщение без удаления старого
    if force_new:
        if want_media:
            return await message.answer_photo(
                photo=photo, caption=text,
                reply_markup=reply_markup, parse_mode='HTML'
            )
        else:
            return await message.answer(
                text=text, reply_markup=reply_markup, parse_mode='HTML',
                link_preview_options=link_preview
            )
            
    try:
        if want_media and is_current_media:
            # Медиа → Медиа: редактируем media + caption
            input_media = InputMediaPhoto(media=photo, caption=text, parse_mode='HTML')
            result = await message.edit_media(media=input_media, reply_markup=reply_markup)
            return result
            
        elif want_media and not is_current_media:
            # Текст → Медиа: удаляем текст, отправляем фото
            try:
                await message.delete()
            except Exception:
                pass
            return await message.answer_photo(
                photo=photo, caption=text,
                reply_markup=reply_markup, parse_mode='HTML'
            )
            
        elif not want_media and not is_current_media:
            # Текст → Текст: обычное редактирование
            return await message.edit_text(
                text=text, reply_markup=reply_markup, parse_mode='HTML',
                link_preview_options=link_preview
            )
            
        else:
            # Медиа → Текст: удаляем медиа, отправляем текст
            try:
                await message.delete()
            except Exception:
                pass
            return await message.answer(
                text=text, reply_markup=reply_markup, parse_mode='HTML',
                link_preview_options=link_preview
            )
            
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        
        if 'message is not modified' in error_msg:
            # Содержимое не изменилось — игнорируем
            logger.debug('Сообщение не изменено, пропускаем')
            return message
            
        if 'there is no text in the message' in error_msg or \
           'message can\'t be edited' in error_msg or \
           'there is no media in the message' in error_msg:
            # Фоллбэк: удаляем и отправляем заново
            try:
                await message.delete()
            except Exception:
                pass
            if want_media:
                return await message.answer_photo(
                    photo=photo, caption=text,
                    reply_markup=reply_markup, parse_mode='HTML'
                )
            else:
                return await message.answer(
                    text=text, reply_markup=reply_markup, parse_mode='HTML',
                    link_preview_options=link_preview
                )
        raise
