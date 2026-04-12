from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

PREMIUM_EMOJI_IDS = {
    "settings": "5870982283724328568",
    "profile": "5870994129244131212",
    "people": "5870772616305839506",
    "person_check": "5891207662678317861",
    "person_cross": "5893192487324880883",
    "file": "5870528606328852614",
    "smile": "5870764288364252592",
    "growth": "5870930636742595124",
    "stats": "5870921681735781843",
    "home": "5873147866364514353",
    "lock_closed": "6037249452824072506",
    "lock_opened": "6037496202990194718",
    "megaphone": "6039422865189638057",
    "check": "5870633910337015697",
    "cross": "5870657884844462243",
    "pencil": "5870676941614354370",
    "trash": "5870875489362513438",
    "down": "5893057118545646106",
    "clip": "6039451237743595514",
    "link": "5769289093221454192",
    "info": "6028435952299413210",
    "bot": "6030400221232501136",
    "eye": "6037397706505195857",
    "hidden": "6037243349675544634",
    "send": "5963103826075456248",
    "download": "6039802767931871481",
    "notification": "6039486778597970865",
    "gift": "6032644646587338669",
    "clock": "5983150113483134607",
    "hurray": "6041731551845159060",
    "font": "5870801517140775623",
    "write": "5870753782874246579",
    "media_photo": "6035128606563241721",
    "geo": "6042011682497106307",
    "wallet": "5769126056262898415",
    "box": "5884479287171485878",
    "cryptobot": "5260752406890711732",
    "calendar": "5890937706803894250",
    "tag": "5886285355279193209",
    "time_passed": "5775896410780079073",
    "apps": "5778672437122045013",
    "brush": "6050679691004612757",
    "add_text": "5771851822897566479",
    "resolution": "5778479949572738874",
    "money": "5904462880941545555",
    "send_money": "5890848474563352982",
    "receive_money": "5879814368572478751",
    "code": "5940433880585605708",
    "loading": "5345906554510012647",
    "back": "◁",
}

EMOJI_REPLACEMENTS = {
    "⬅️": PREMIUM_EMOJI_IDS["back"],
    "◀️": PREMIUM_EMOJI_IDS["back"],
    "❓": "ℹ️",
    "📢": "📣",
    "📄": "📁",
    "📋": "📁",
    "📝": "✍️",
    "✏️": "✍️",
    "🔑": "🔐",
    "💳": "💵",
    "💰": "💵",
    "💎": "👛",
    "📥": "⬇️",
    "📤": "⬆️",
    "🈴": "🏠",
}


def normalize_button_text(text: str) -> str:
    if not text:
        return text
    normalized = text
    for old, new in EMOJI_REPLACEMENTS.items():
        if normalized.startswith(old):
            normalized = normalized.replace(old, new, 1)
            break
    return normalized


def normalize_markup_emojis(markup: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup | None:
    if not markup:
        return markup
    for row in markup.inline_keyboard:
        for button in row:
            if isinstance(button, InlineKeyboardButton) and button.text:
                button.text = normalize_button_text(button.text)
    return markup


if not getattr(InlineKeyboardBuilder, "_premium_emoji_patch_applied", False):
    _original_as_markup = InlineKeyboardBuilder.as_markup

    def _as_markup_with_premium_emojis(self, *args, **kwargs):
        return normalize_markup_emojis(_original_as_markup(self, *args, **kwargs))

    InlineKeyboardBuilder.as_markup = _as_markup_with_premium_emojis
    InlineKeyboardBuilder._premium_emoji_patch_applied = True
