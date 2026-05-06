"""
Роутер статистики для админ-панели.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db_statistics import (
    get_new_users_stats,
    get_subscriptions_stats,
    get_active_connections_stats,
    get_revenue_stats,
    get_traffic_stats,
)
from bot.utils.admin import is_admin
from bot.utils.text import safe_edit_or_send, escape_html
from bot.keyboards.admin_misc import back_button, home_button

logger = logging.getLogger(__name__)

router = Router()


def statistics_menu_kb():
    """Клавиатура меню статистики."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='👥 Пользователи', callback_data='admin_stats_users'),
        InlineKeyboardButton(text='🔑 Подписки', callback_data='admin_stats_subscriptions')
    )
    builder.row(
        InlineKeyboardButton(text='📊 Активность', callback_data='admin_stats_activity'),
        InlineKeyboardButton(text='💰 Доходы', callback_data='admin_stats_revenue')
    )
    builder.row(
        InlineKeyboardButton(text='📈 Трафик', callback_data='admin_stats_traffic'),
        InlineKeyboardButton(text='🔄 Обновить все', callback_data='admin_statistics')
    )
    builder.row(back_button('admin_panel'), home_button())
    return builder.as_markup()


def stats_detail_kb():
    """Клавиатура для детальной статистики."""
    builder = InlineKeyboardBuilder()
    builder.row(back_button('admin_statistics'), home_button())
    return builder.as_markup()


@router.callback_query(F.data == 'admin_statistics')
async def show_statistics_menu(callback: CallbackQuery):
    """Показывает главное меню статистики."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    text = (
        "📊 <b>Статистика</b>\n\n"
        "Выберите раздел для просмотра детальной статистики:\n\n"
        "👥 <b>Пользователи</b> — новые регистрации\n"
        "🔑 <b>Подписки</b> — покупки и активность\n"
        "📊 <b>Активность</b> — использование VPN\n"
        "💰 <b>Доходы</b> — финансовая статистика\n"
        "📈 <b>Трафик</b> — использование трафика"
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=statistics_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == 'admin_stats_users')
async def show_users_statistics(callback: CallbackQuery):
    """Показывает статистику по пользователям."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    try:
        stats = get_new_users_stats()
        
        text = (
            "👥 <b>Статистика пользователей</b>\n\n"
            f"📅 <b>За последние 24 часа:</b> {stats['day']}\n"
            f"📅 <b>За последние 7 дней:</b> {stats['week']}\n"
            f"📅 <b>За последние 30 дней:</b> {stats['month']}\n"
            f"📅 <b>За последний год:</b> {stats['year']}\n\n"
            f"👤 <b>Всего пользователей:</b> {stats['total']}"
        )
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователей: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_subscriptions')
async def show_subscriptions_statistics(callback: CallbackQuery):
    """Показывает статистику по подпискам."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    try:
        stats = get_subscriptions_stats()
        
        text = (
            "🔑 <b>Статистика подписок</b>\n\n"
            "<b>Куплено подписок:</b>\n"
            f"📅 За последние 24 часа: {stats['day']}\n"
            f"📅 За последние 7 дней: {stats['week']}\n"
            f"📅 За последние 30 дней: {stats['month']}\n"
            f"📅 За последний год: {stats['year']}\n\n"
            f"📊 <b>Всего подписок:</b> {stats['total']}\n"
            f"🟢 <b>Активных:</b> {stats['active']}\n"
            f"🔴 <b>Истекших:</b> {stats['expired']}"
        )
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики подписок: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_activity')
async def show_activity_statistics(callback: CallbackQuery):
    """Показывает статистику активности (использования VPN)."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    try:
        stats = get_active_connections_stats()
        
        text = (
            "📊 <b>Статистика активности</b>\n\n"
            "<b>Пользователи, использующие VPN:</b>\n"
            f"📅 За последние 24 часа: {stats['day']}\n"
            f"📅 За последние 7 дней: {stats['week']}\n"
            f"📅 За последние 30 дней: {stats['month']}\n\n"
            f"👥 <b>Всего пользователей с трафиком:</b> {stats['total_with_traffic']}\n\n"
            "<i>💡 Активность определяется по наличию трафика и обновлению данных</i>"
        )
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики активности: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_revenue')
async def show_revenue_statistics(callback: CallbackQuery):
    """Показывает статистику доходов."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    try:
        stats = get_revenue_stats()
        
        def format_revenue(period_stats):
            """Форматирует доходы за период."""
            lines = []
            if period_stats['total_rub'] > 0:
                lines.append(f"💳 {period_stats['total_rub']:.2f} ₽")
            if period_stats['total_usd'] > 0:
                lines.append(f"💵 ${period_stats['total_usd']:.2f}")
            if period_stats['total_stars'] > 0:
                lines.append(f"⭐ {period_stats['total_stars']}")
            if not lines:
                return "0"
            return " + ".join(lines)
        
        text = (
            "💰 <b>Статистика доходов</b>\n\n"
            f"<b>За последние 24 часа:</b>\n"
            f"  Платежей: {stats['day']['count']}\n"
            f"  Сумма: {format_revenue(stats['day'])}\n\n"
            f"<b>За последние 7 дней:</b>\n"
            f"  Платежей: {stats['week']['count']}\n"
            f"  Сумма: {format_revenue(stats['week'])}\n\n"
            f"<b>За последние 30 дней:</b>\n"
            f"  Платежей: {stats['month']['count']}\n"
            f"  Сумма: {format_revenue(stats['month'])}\n\n"
            f"<b>За последний год:</b>\n"
            f"  Платежей: {stats['year']['count']}\n"
            f"  Сумма: {format_revenue(stats['year'])}\n\n"
            f"<b>Всего за все время:</b>\n"
            f"  Платежей: {stats['total']['count']}\n"
            f"  Сумма: {format_revenue(stats['total'])}"
        )
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики доходов: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data.startswith('admin_stats_traffic'))
async def show_traffic_statistics(callback: CallbackQuery):
    """Показывает статистику использования трафика с пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    try:
        # Парсим номер страницы из callback_data
        # Формат: admin_stats_traffic или admin_stats_traffic:page
        parts = callback.data.split(':')
        page = int(parts[1]) if len(parts) > 1 else 1
        
        stats = get_traffic_stats(page=page, per_page=10)
        
        text = (
            "📈 <b>Статистика трафика</b>\n\n"
            f"📊 <b>Всего использовано:</b> {stats['total_used_gb']:.2f} ГБ\n"
            f"👤 <b>Средний трафик на пользователя:</b> {stats['avg_per_user_gb']:.2f} ГБ\n"
            f"👥 <b>Всего пользователей с трафиком:</b> {stats['total_users']}\n\n"
        )
        
        if stats['top_users']:
            text += f"<b>🏆 Топ пользователей по трафику (стр. {stats['current_page']}/{stats['total_pages']}):</b>\n"
            # Вычисляем глобальный номер пользователя
            start_num = (stats['current_page'] - 1) * 10 + 1
            for i, user in enumerate(stats['top_users'], start_num):
                username = f"@{user['username']}" if user['username'] else f"ID: {user['telegram_id']}"
                text += f"{i}. {escape_html(username)} — {user['traffic_gb']:.2f} ГБ\n"
        else:
            text += "<i>Нет данных о трафике</i>"
        
        # Создаём клавиатуру с пагинацией
        builder = InlineKeyboardBuilder()
        
        # Кнопки навигации
        nav_buttons = []
        if stats['current_page'] > 1:
            nav_buttons.append(InlineKeyboardButton(
                text='◀️ Назад',
                callback_data=f'admin_stats_traffic:{stats["current_page"] - 1}'
            ))
        if stats['current_page'] < stats['total_pages']:
            nav_buttons.append(InlineKeyboardButton(
                text='Вперёд ▶️',
                callback_data=f'admin_stats_traffic:{stats["current_page"] + 1}'
            ))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        # Кнопки возврата
        builder.row(back_button('admin_statistics'), home_button())
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики трафика: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)
