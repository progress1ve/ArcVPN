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
    get_payers_stats,
    get_online_users,
    get_servers_stats,
    get_conversion_stats,
    get_recent_payments,
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
        InlineKeyboardButton(text='💳 Плательщики', callback_data='admin_stats_payers')
    )
    builder.row(
        InlineKeyboardButton(text='🟢 Онлайн', callback_data='admin_stats_online'),
        InlineKeyboardButton(text='🖥️ Серверы', callback_data='admin_stats_servers')
    )
    builder.row(
        InlineKeyboardButton(text='🔄 Конверсия', callback_data='admin_stats_conversion'),
        InlineKeyboardButton(text='📋 Платежи', callback_data='admin_stats_recent_payments')
    )
    builder.row(
        InlineKeyboardButton(text='🔄 Обновить', callback_data='admin_statistics')
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
        "📈 <b>Трафик</b> — использование трафика\n"
        "💳 <b>Плательщики</b> — кто сколько оплатил\n"
        "🟢 <b>Онлайн</b> — активные пользователи сейчас\n"
        "🖥️ <b>Серверы</b> — статистика по серверам\n"
        "🔄 <b>Конверсия</b> — пробные → платные\n"
        "📋 <b>Платежи</b> — последние платежи"
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
            f"🔴 <b>Истёкших:</b> {stats['expired']}"
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
            f"👤 <b>Всего пользователей с трафиком:</b> {stats['total_with_traffic']}\n\n"
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
            f"<b>Всего за всё время:</b>\n"
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


@router.callback_query(F.data.startswith('admin_stats_payers'))
async def show_payers_statistics(callback: CallbackQuery):
    """Показывает статистику плательщиков с пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        # Парсим номер страницы
        parts = callback.data.split(':')
        page = int(parts[1]) if len(parts) > 1 else 1

        stats = get_payers_stats(page=page, per_page=10)

        text = (
            "💳 <b>Статистика плательщиков</b>\n\n"
            f"👥 <b>Всего плательщиков:</b> {stats['total_payers']}\n"
            f"📋 <b>Всего платежей:</b> {stats['total_payments']}\n"
            f"💰 <b>Общая сумма:</b>\n"
        )
        
        if stats['total_rub'] > 0:
            text += f"   💳 {stats['total_rub']:.2f} ₽\n"
        if stats['total_usd'] > 0:
            text += f"   💵 ${stats['total_usd']:.2f}\n"
        if stats['total_stars'] > 0:
            text += f"   ⭐ {stats['total_stars']}\n"
        
        text += f"\n<b>🏆 Топ плательщиков (стр. {stats['current_page']}/{stats['total_pages']}):</b>\n"
        
        start_num = (stats['current_page'] - 1) * 10 + 1
        for i, payer in enumerate(stats['payers'], start_num):
            username = f"@{payer['username']}" if payer['username'] else f"ID: {payer['telegram_id']}"
            text += f"{i}. {escape_html(username)} — {payer['payment_count']} плат."
            if payer['total_rub'] > 0:
                text += f" ({payer['total_rub']:.0f}₽)"
            text += "\n"

        # Клавиатура с пагинацией
        builder = InlineKeyboardBuilder()

        nav_buttons = []
        if stats['current_page'] > 1:
            nav_buttons.append(InlineKeyboardButton(
                text='◀️ Назад',
                callback_data=f'admin_stats_payers:{stats["current_page"] - 1}'
            ))
        if stats['current_page'] < stats['total_pages']:
            nav_buttons.append(InlineKeyboardButton(
                text='Вперёд ▶️',
                callback_data=f'admin_stats_payers:{stats["current_page"] + 1}'
            ))

        if nav_buttons:
            builder.row(*nav_buttons)

        builder.row(back_button('admin_statistics'), home_button())

        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении статистики плательщиков: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_online')
async def show_online_statistics(callback: CallbackQuery):
    """Показывает пользователей онлайн."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        stats = get_online_users()

        text = (
            "🟢 <b>Пользователи онлайн</b>\n\n"
            f"👥 <b>Всего активных подписок:</b> {stats['count']}\n\n"
        )

        if stats['users']:
            text += "<b>Список активных пользователей:</b>\n\n"
            for user in stats['users'][:30]:  # Показываем первых 30
                username = f"@{user['username']}" if user['username'] else f"ID: {user['telegram_id']}"
                text += f"• {escape_html(username)}\n"
            
            if len(stats['users']) > 30:
                text += f"\n<i>... и ещё {len(stats['users']) - 30} пользователей</i>"
        else:
            text += "<i>Нет активных пользователей</i>"

        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении статистики онлайн: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_servers')
async def show_servers_statistics(callback: CallbackQuery):
    """Показывает статистику по серверам."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        servers = get_servers_stats()

        text = "🖥️ <b>Статистика по серверам</b>\n\n"

        total_clients = 0
        total_active = 0
        total_traffic = 0

        for server in servers:
            status = "🟢" if server['is_active'] else "🔴"
            text += (
                f"{status} <b>{escape_html(server['name'])}</b>\n"
                f"   👥 Клиентов: {server['clients_count']}\n"
                f"   🟢 Активных: {server['active_clients']}\n"
                f"   📈 Трафик: {server['total_traffic_gb']:.2f} ГБ\n\n"
            )
            total_clients += server['clients_count']
            total_active += server['active_clients']
            total_traffic += server['total_traffic_gb']

        text += (
            f"<b>📊 Итого:</b>\n"
            f"   👥 Всего клиентов: {total_clients}\n"
            f"   🟢 Активных: {total_active}\n"
            f"   📈 Общий трафик: {total_traffic:.2f} ГБ"
        )

        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении статистики серверов: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_conversion')
async def show_conversion_statistics(callback: CallbackQuery):
    """Показывает статистику конверсии."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        stats = get_conversion_stats()

        text = (
            "🔄 <b>Статистика конверсии</b>\n\n"
            f"🎯 <b>Пробные → Платные</b>\n\n"
            f"👥 Пользователей с пробным периодом: {stats['trial_users']}\n"
            f"👥 Пользователей с платными подписками: {stats['paid_users']}\n"
            f"✅ Конвертировались (пробный → платный): {stats['converted']}\n\n"
            f"📊 <b>Конверсия:</b> {stats['conversion_rate']:.1f}%\n\n"
            "<i>💡 Конверсия показывает процент пользователей, которые после пробного периода оформили платную подписку</i>"
        )

        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении статистики конверсии: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == 'admin_stats_recent_payments')
async def show_recent_payments(callback: CallbackQuery):
    """Показывает последние платежи."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        payments = get_recent_payments(limit=20)

        text = "📋 <b>Последние платежи</b>\n\n"

        if payments:
            for p in payments:
                username = f"@{p['username']}" if p['username'] else f"ID: {p['telegram_id']}"
                
                # Форматируем сумму
                amount = ""
                if p['price_rub']:
                    amount = f"{p['price_rub']}₽"
                elif p['amount_cents']:
                    amount = f"${p['amount_cents']/100:.2f}"
                elif p['amount_stars']:
                    amount = f"⭐{p['amount_stars']}"
                
                # Тип платежа
                payment_type = {
                    'yookassa': '💳',
                    'yookassa_qr': '📱',
                    'crypto': '🪙',
                    'stars': '⭐',
                    'trial': '🎁'
                }.get(p['payment_type'], '💰')
                
                text += f"{payment_type} {escape_html(username)} — {amount}\n"
                text += f"   {p['tariff_name'] or 'N/A'} • {p['paid_at'][:16]}\n\n"
        else:
            text += "<i>Нет платежей</i>"

        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=stats_detail_kb()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении последних платежей: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)
