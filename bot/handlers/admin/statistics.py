"""
Роутер статистики для админ-панели.

Один экран-сводка со всеми ключевыми метриками (пользователи, подписки, доход,
онлайн, конверсия, трафик) + drill-down списки там, где это реально списки
(топ плательщиков, топ по трафику, последние платежи, серверы, кто онлайн).
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.db_statistics import (
    get_new_users_stats,
    get_subscriptions_stats,
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


# ============================================================================
# ФОРМАТИРОВАНИЕ
# ============================================================================

def _fmt_money(period: dict) -> str:
    """Сумма за период в виде «1500₽ + $4.20 + ⭐300» (только ненулевые части)."""
    parts = []
    if period.get('total_rub', 0) > 0:
        parts.append(f"{period['total_rub']:.0f}₽")
    if period.get('total_usd', 0) > 0:
        parts.append(f"${period['total_usd']:.2f}")
    if period.get('total_stars', 0) > 0:
        parts.append(f"⭐{period['total_stars']}")
    return " + ".join(parts) if parts else "—"


def _user_label(row: dict) -> str:
    """@username или ID: 12345."""
    if row.get('username'):
        return f"@{escape_html(row['username'])}"
    return f"ID: {row['telegram_id']}"


def build_dashboard_text() -> str:
    """Собирает текст сводки из всех источников статистики."""
    users = get_new_users_stats()
    subs = get_subscriptions_stats()
    rev = get_revenue_stats()
    conv = get_conversion_stats()
    online = get_online_users()
    traffic = get_traffic_stats(page=1, per_page=1)

    now = datetime.now().strftime('%d.%m %H:%M')

    lines = [
        "📊 <b>Статистика ArcVPN</b>",
        f"<i>на {now}</i>",
        "",
        "👥 <b>Пользователи</b>",
        f"Всего: <b>{users['total']}</b>",
        f"+{users['day']} сутки · +{users['week']} нед · +{users['month']} мес",
        "",
        "🔑 <b>Подписки</b>",
        f"Активных: <b>{subs['active']}</b> · истекло: {subs['expired']}",
        f"Куплено: {subs['day']} / {subs['week']} / {subs['month']} (сутки/нед/мес)",
        "",
        "💰 <b>Доход</b>",
        f"Сутки: <b>{_fmt_money(rev['day'])}</b> · {rev['day']['count']} плат.",
        f"Неделя: <b>{_fmt_money(rev['week'])}</b> · {rev['week']['count']} плат.",
        f"Месяц: <b>{_fmt_money(rev['month'])}</b> · {rev['month']['count']} плат.",
        f"Всего: <b>{_fmt_money(rev['total'])}</b> · {rev['total']['count']} плат.",
        "",
        f"🟢 Активных подписок: <b>{online['count']}</b>",
        f"🔄 Конверсия trial→платный: <b>{conv['conversion_rate']:.0f}%</b> "
        f"({conv['converted']}/{conv['trial_users']})",
        f"📈 Трафик: <b>{traffic['total_used_gb']:.1f} ГБ</b> всего · "
        f"~{traffic['avg_per_user_gb']:.1f} ГБ/чел",
    ]
    return "\n".join(lines)


# ============================================================================
# КЛАВИАТУРЫ
# ============================================================================

def statistics_menu_kb():
    """Сводка: drill-down списки + обновление."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='💳 Топ плательщиков', callback_data='admin_stats_payers'),
        InlineKeyboardButton(text='📈 Топ по трафику', callback_data='admin_stats_traffic'),
    )
    builder.row(
        InlineKeyboardButton(text='📋 Последние платежи', callback_data='admin_stats_recent_payments'),
        InlineKeyboardButton(text='🖥️ Серверы', callback_data='admin_stats_servers'),
    )
    builder.row(
        InlineKeyboardButton(text='🟢 Кто онлайн', callback_data='admin_stats_online'),
        InlineKeyboardButton(text='🔄 Обновить', callback_data='admin_statistics'),
    )
    builder.row(back_button('admin_panel'), home_button())
    return builder.as_markup()


def stats_detail_kb():
    """Клавиатура для drill-down экрана (назад к сводке)."""
    builder = InlineKeyboardBuilder()
    builder.row(back_button('admin_statistics'), home_button())
    return builder.as_markup()


# ============================================================================
# СВОДКА
# ============================================================================

@router.callback_query(F.data == 'admin_statistics')
async def show_statistics_menu(callback: CallbackQuery):
    """Показывает сводку со всеми ключевыми метриками на одном экране."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        text = build_dashboard_text()
    except Exception as e:
        logger.error(f"Ошибка сборки сводки статистики: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)
        return

    await safe_edit_or_send(callback.message, text, reply_markup=statistics_menu_kb())
    await callback.answer()


# ============================================================================
# DRILL-DOWN: ТОП ПО ТРАФИКУ
# ============================================================================

@router.callback_query(F.data.startswith('admin_stats_traffic'))
async def show_traffic_statistics(callback: CallbackQuery):
    """Топ пользователей по трафику с пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        parts = callback.data.split(':')
        page = int(parts[1]) if len(parts) > 1 else 1

        stats = get_traffic_stats(page=page, per_page=10)

        text = (
            "📈 <b>Трафик</b>\n\n"
            f"Всего: <b>{stats['total_used_gb']:.1f} ГБ</b> · "
            f"~{stats['avg_per_user_gb']:.1f} ГБ/чел · "
            f"{stats['total_users']} чел.\n\n"
        )

        if stats['top_users']:
            text += f"<b>🏆 Топ (стр. {stats['current_page']}/{stats['total_pages']})</b>\n"
            start_num = (stats['current_page'] - 1) * 10 + 1
            for i, user in enumerate(stats['top_users'], start_num):
                text += f"{i}. {_user_label(user)} — {user['traffic_gb']:.2f} ГБ\n"
        else:
            text += "<i>Нет данных о трафике</i>"

        builder = InlineKeyboardBuilder()
        nav = []
        if stats['current_page'] > 1:
            nav.append(InlineKeyboardButton(text='◀️', callback_data=f'admin_stats_traffic:{stats["current_page"] - 1}'))
        if stats['current_page'] < stats['total_pages']:
            nav.append(InlineKeyboardButton(text='▶️', callback_data=f'admin_stats_traffic:{stats["current_page"] + 1}'))
        if nav:
            builder.row(*nav)
        builder.row(back_button('admin_statistics'), home_button())

        await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка статистики трафика: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


# ============================================================================
# DRILL-DOWN: ТОП ПЛАТЕЛЬЩИКОВ
# ============================================================================

@router.callback_query(F.data.startswith('admin_stats_payers'))
async def show_payers_statistics(callback: CallbackQuery):
    """Топ плательщиков с пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        parts = callback.data.split(':')
        page = int(parts[1]) if len(parts) > 1 else 1

        stats = get_payers_stats(page=page, per_page=10)

        total_money = _fmt_money({
            'total_rub': stats['total_rub'],
            'total_usd': stats['total_usd'],
            'total_stars': stats['total_stars'],
        })

        text = (
            "💳 <b>Плательщики</b>\n\n"
            f"Всего: <b>{stats['total_payers']}</b> чел. · "
            f"{stats['total_payments']} плат.\n"
            f"Сумма: <b>{total_money}</b>\n\n"
        )

        if stats['payers']:
            text += f"<b>🏆 Топ (стр. {stats['current_page']}/{stats['total_pages']})</b>\n"
            start_num = (stats['current_page'] - 1) * 10 + 1
            for i, payer in enumerate(stats['payers'], start_num):
                text += f"{i}. {_user_label(payer)} — {payer['payment_count']} плат."
                if payer['total_rub'] > 0:
                    text += f" · {payer['total_rub']:.0f}₽"
                text += "\n"
        else:
            text += "<i>Платежей пока нет</i>"

        builder = InlineKeyboardBuilder()
        nav = []
        if stats['current_page'] > 1:
            nav.append(InlineKeyboardButton(text='◀️', callback_data=f'admin_stats_payers:{stats["current_page"] - 1}'))
        if stats['current_page'] < stats['total_pages']:
            nav.append(InlineKeyboardButton(text='▶️', callback_data=f'admin_stats_payers:{stats["current_page"] + 1}'))
        if nav:
            builder.row(*nav)
        builder.row(back_button('admin_statistics'), home_button())

        await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка статистики плательщиков: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


# ============================================================================
# DRILL-DOWN: КТО ОНЛАЙН
# ============================================================================

@router.callback_query(F.data == 'admin_stats_online')
async def show_online_statistics(callback: CallbackQuery):
    """Список пользователей с активными подписками."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        stats = get_online_users()

        text = f"🟢 <b>Активные подписки: {stats['count']}</b>\n\n"

        if stats['users']:
            for user in stats['users'][:40]:
                text += f"• {_user_label(user)}\n"
            if len(stats['users']) > 40:
                text += f"\n<i>… и ещё {len(stats['users']) - 40}</i>"
        else:
            text += "<i>Нет активных подписок</i>"

        await safe_edit_or_send(callback.message, text, reply_markup=stats_detail_kb())
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка статистики онлайн: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


# ============================================================================
# DRILL-DOWN: СЕРВЕРЫ
# ============================================================================

@router.callback_query(F.data == 'admin_stats_servers')
async def show_servers_statistics(callback: CallbackQuery):
    """Статистика по серверам."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        servers = get_servers_stats()

        text = "🖥️ <b>Серверы</b>\n\n"
        total_clients = total_active = 0
        total_traffic = 0.0

        if not servers:
            text += "<i>Серверов пока нет</i>"
        else:
            for s in servers:
                status = "🟢" if s['is_active'] else "🔴"
                text += (
                    f"{status} <b>{escape_html(s['name'])}</b> — "
                    f"{s['active_clients']}/{s['clients_count']} активны · "
                    f"{s['total_traffic_gb']:.1f} ГБ\n"
                )
                total_clients += s['clients_count']
                total_active += s['active_clients']
                total_traffic += s['total_traffic_gb']

            text += (
                f"\n<b>Итого:</b> {total_active}/{total_clients} активны · "
                f"{total_traffic:.1f} ГБ"
            )

        await safe_edit_or_send(callback.message, text, reply_markup=stats_detail_kb())
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка статистики серверов: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


# ============================================================================
# DRILL-DOWN: ПОСЛЕДНИЕ ПЛАТЕЖИ
# ============================================================================

@router.callback_query(F.data == 'admin_stats_recent_payments')
async def show_recent_payments(callback: CallbackQuery):
    """Последние платежи."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return

    try:
        payments = get_recent_payments(limit=20)

        text = "📋 <b>Последние платежи</b>\n\n"

        if payments:
            for p in payments:
                amount = ""
                if p['price_rub']:
                    amount = f"{p['price_rub']:.0f}₽"
                elif p['amount_cents']:
                    amount = f"${p['amount_cents'] / 100:.2f}"
                elif p['amount_stars']:
                    amount = f"⭐{p['amount_stars']}"

                icon = {
                    'yookassa': '💳', 'yookassa_qr': '📱', 'cards': '💳',
                    'crypto': '🪙', 'stars': '⭐', 'trial': '🎁',
                }.get(p['payment_type'], '💰')

                when = (p['paid_at'] or '')[:16].replace('T', ' ')
                text += f"{icon} {_user_label(p)} — {amount or '—'}\n"
                text += f"   {escape_html(p['tariff_name'] or 'Подписка')} · {when}\n"
        else:
            text += "<i>Платежей пока нет</i>"

        await safe_edit_or_send(callback.message, text, reply_markup=stats_detail_kb())
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка последних платежей: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)
