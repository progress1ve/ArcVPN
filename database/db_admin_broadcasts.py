"""Reviewed Telegram campaigns. All grants and recipient state are durable."""
import html
import json
import re
import secrets
import sqlite3
from html.parser import HTMLParser
from urllib.parse import urlsplit

from database.connection import get_db


def create_schema(conn):
    schema = """
        CREATE TABLE IF NOT EXISTS admin_broadcasts (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, payload TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'draft',
            tested_revision INTEGER, tested_admin INTEGER, tested_at TEXT,
            created_by TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP, started_at TEXT, completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS admin_broadcast_recipients (
            campaign_id INTEGER NOT NULL REFERENCES admin_broadcasts(id),
            user_id INTEGER NOT NULL REFERENCES users(id), telegram_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            retry_at TEXT, error TEXT, message_id INTEGER, sent_at TEXT,
            key_id INTEGER, reward_state TEXT NOT NULL DEFAULT 'pending',
            promo_code TEXT, promo_id INTEGER, PRIMARY KEY(campaign_id,user_id)
        );
        CREATE INDEX IF NOT EXISTS admin_broadcast_pending
            ON admin_broadcast_recipients(campaign_id,status,retry_at);
        CREATE TABLE IF NOT EXISTS broadcast_personal_promos (
            promocode_id INTEGER PRIMARY KEY REFERENCES promocodes(id),
            user_id INTEGER NOT NULL REFERENCES users(id)
        );
        CREATE TRIGGER IF NOT EXISTS broadcast_personal_order_insert
        BEFORE INSERT ON payments
        WHEN NEW.promocode_id IN (SELECT promocode_id FROM broadcast_personal_promos)
        BEGIN
            SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM broadcast_personal_promos WHERE promocode_id=NEW.promocode_id AND user_id=NEW.user_id)
                OR EXISTS(SELECT 1 FROM payments WHERE promocode_id=NEW.promocode_id AND status IN ('pending','paid','succeeded'))
                THEN RAISE(ABORT,'personal_promocode_reserved') END;
        END;
        CREATE TRIGGER IF NOT EXISTS broadcast_personal_order_update
        BEFORE UPDATE OF promocode_id,user_id,status ON payments
        WHEN NEW.promocode_id IN (SELECT promocode_id FROM broadcast_personal_promos) AND NEW.status IN ('pending','paid','succeeded')
        BEGIN
            SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM broadcast_personal_promos WHERE promocode_id=NEW.promocode_id AND user_id=NEW.user_id)
                OR EXISTS(SELECT 1 FROM payments WHERE promocode_id=NEW.promocode_id AND id!=NEW.id AND status IN ('pending','paid','succeeded'))
                THEN RAISE(ABORT,'personal_promocode_reserved') END;
        END;
    """
    # executescript commits an outer transaction. Keep the migration atomic by
    # executing complete statements individually (triggers contain semicolons).
    statement = ''
    for line in schema.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ''


def safe_url(value):
    value = str(value or '').strip()
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or any(ord(c) < 32 for c in value) or len(value) > 1024):
        raise ValueError('Ссылка должна быть корректным HTTPS-адресом')
    return value


def create_promo_order_guards(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS broadcast_campaign_promos (
        promocode_id INTEGER PRIMARY KEY REFERENCES promocodes(id))''')
    conn.execute('INSERT OR IGNORE INTO broadcast_campaign_promos SELECT promocode_id FROM broadcast_personal_promos')
    for operation in ('INSERT', 'UPDATE OF promocode_id,user_id,status'):
        name = 'insert' if operation == 'INSERT' else 'update'
        exclude_current = '' if operation == 'INSERT' else ' AND id!=NEW.id'
        new_reservation = '1' if operation == 'INSERT' else "(OLD.promocode_id IS NOT NEW.promocode_id OR OLD.user_id IS NOT NEW.user_id OR OLD.status NOT IN ('pending','paid','succeeded'))"
        conn.execute(f'''CREATE TRIGGER IF NOT EXISTS broadcast_campaign_order_{name}
            BEFORE {operation} ON payments
            WHEN NEW.promocode_id IN (SELECT promocode_id FROM broadcast_campaign_promos)
                AND NEW.status IN ('pending','paid','succeeded')
            BEGIN
                SELECT CASE WHEN EXISTS(SELECT 1 FROM payments WHERE promocode_id=NEW.promocode_id
                    AND user_id=NEW.user_id AND status IN ('pending','paid','succeeded'){exclude_current})
                    OR ({new_reservation} AND (SELECT COUNT(*) FROM payments WHERE promocode_id=NEW.promocode_id
                        AND status IN ('pending','paid','succeeded'){exclude_current}) >=
                        (SELECT max_uses FROM promocodes WHERE id=NEW.promocode_id))
                    OR ({new_reservation} AND NOT EXISTS(SELECT 1 FROM promocodes WHERE id=NEW.promocode_id AND is_active=1
                        AND datetime(expires_at)>datetime('now')))
                    THEN RAISE(ABORT,'campaign_promocode_reserved_or_expired') END;
            END''')


class TelegramHTML(HTMLParser):
    tags = {'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'del', 'code', 'pre', 'a', 'blockquote', 'tg-spoiler'}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            raise ValueError(f'Telegram не поддерживает тег <{tag}>')
        if tag == 'a':
            if len(attrs) != 1 or attrs[0][0] != 'href':
                raise ValueError('У ссылки разрешён только href')
            safe_url(attrs[0][1])
        elif attrs:
            raise ValueError('Атрибуты форматирования не поддерживаются')
        if any(t in {'code', 'pre', 'a'} for t in self.stack):
            raise ValueError('Внутри ссылки или кода вложенные теги не поддерживаются')
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError('HTML-теги должны быть правильно вложены и закрыты')

    def handle_startendtag(self, tag, attrs):
        raise ValueError('Для переноса строки используйте Enter, а не HTML-тег')

    def handle_data(self, data):
        if '<' in data or re.search(r'&(?![A-Za-z0-9#])', data):
            raise ValueError('Символы < и & нужно экранировать: &lt; и &amp;')
        self.text.append(data)

    def handle_entityref(self, name):
        if name not in {'lt', 'gt', 'amp', 'quot'}:
            raise ValueError('Неподдерживаемая HTML-сущность')
        self.text.append(html.unescape(f'&{name};'))

    def handle_charref(self, name):
        try:
            value = int(name[1:], 16) if name.startswith(('x', 'X')) else int(name)
            if value == 0 or value > 0x10ffff or 0xd800 <= value <= 0xdfff:
                raise ValueError()
            self.text.append(chr(value))
        except ValueError:
            raise ValueError('Некорректная HTML-сущность') from None

    def handle_comment(self, data):
        raise ValueError('HTML-комментарии не поддерживаются')

    def handle_decl(self, decl):
        raise ValueError('HTML-документ не поддерживается; введите текст сообщения')

    def handle_pi(self, data):
        raise ValueError('HTML-инструкции не поддерживаются')

    def unknown_decl(self, data):
        raise ValueError('HTML-декларации не поддерживаются')


def validate_html(text, limit=4096):
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise ValueError('Введите сообщение')
    # Reject malformed entities rather than relying on HTMLParser recovery.
    if re.search(r'&(?!lt;|gt;|amp;|quot;|#\d+;|#[xX][0-9a-fA-F]+;)', text):
        raise ValueError('Некорректный символ &: используйте &amp;')
    parser = TelegramHTML()
    parser.feed(text)
    parser.close()
    if parser.stack:
        raise ValueError('Закройте все HTML-теги')
    visible = ''.join(parser.text)
    if not visible.strip() or len(visible.encode('utf-16-le')) // 2 > limit:
        raise ValueError(f'Сообщение превышает лимит {limit} символов Telegram')
    return text


def integer(value, minimum, maximum, label):
    if isinstance(value, bool) or not re.fullmatch(r'\d+', str(value)):
        raise ValueError(f'{label}: нужно целое число')
    result = int(value)
    if not minimum <= result <= maximum:
        raise ValueError(f'{label}: допустимо от {minimum} до {maximum}')
    return result


def validate_payload(data):
    if not isinstance(data, dict):
        raise ValueError('Некорректный черновик')
    audience = data.get('audience') or {}
    reward = data.get('reward') or {}
    if not isinstance(audience, dict) or not isinstance(reward, dict):
        raise ValueError('Некорректные настройки')
    segment = audience.get('segment', 'all')
    if segment not in {'all', 'active', 'expired', 'never_paid', 'expiring', 'selected'}:
        raise ValueError('Выберите аудиторию')
    chosen = {}
    for key in ('selected', 'excluded'):
        values = audience.get(key) or []
        if not isinstance(values, list) or len(values) > 2000:
            raise ValueError('Некорректный список пользователей')
        chosen[key] = sorted({integer(v, 1, 2**53 - 1, 'Пользователь') for v in values})
    chosen.update(segment=segment, tariff_id=integer(audience.get('tariff_id') or 0, 0, 1000000, 'Тариф'),
                  expiring_days=integer(audience.get('expiring_days') or 7, 1, 365, 'Срок'))
    kind = reward.get('kind', 'none')
    if kind not in {'none', 'days', 'existing_promo', 'new_promo', 'personal_discount'}:
        raise ValueError('Выберите предложение')
    offer = {'kind': kind}
    if kind == 'days':
        offer['days'] = integer(reward.get('days'), 1, 365, 'Бонусные дни')
    if kind == 'existing_promo':
        offer['promo_id'] = integer(reward.get('promo_id'), 1, 2**31 - 1, 'Промокод')
    if kind in {'new_promo', 'personal_discount'}:
        dtype = reward.get('discount_type', 'percent')
        if dtype not in {'percent', 'fixed'}:
            raise ValueError('Выберите тип скидки')
        offer.update(discount_type=dtype, discount_value=integer(reward.get('discount_value'), 1,
                     100 if dtype == 'percent' else 1000000, 'Скидка'),
                     duration_days=integer(reward.get('duration_days'), 1, 3650, 'Срок скидки'),
                     max_uses=integer(reward.get('max_uses') or 100, 1, 1000000, 'Использования'))
        if kind == 'new_promo':
            code = str(reward.get('code') or '').strip().upper()
            if not re.fullmatch(r'[A-Z0-9_-]{3,32}', code):
                raise ValueError('Код: 3–32 латинских буквы, цифры, _ или -')
            offer['code'] = code
    photo = str(data.get('photo_file_id') or '').strip()
    if len(photo) > 512 or (photo and not re.fullmatch(r'[A-Za-z0-9_-]+', photo)):
        raise ValueError('Некорректный Telegram file_id фотографии')
    buttons = data.get('buttons') or []
    if not isinstance(buttons, list) or len(buttons) > 3:
        raise ValueError('Допустимо до трёх кнопок')
    clean_buttons = []
    for button in buttons:
        label = str(button.get('text') or '').strip()
        if not label or len(label) > 40:
            raise ValueError('Текст кнопки: 1–40 символов')
        clean_buttons.append({'text': label, 'url': safe_url(button.get('url'))})
    title = str(data.get('title') or '').strip()
    if not title or len(title) > 100:
        raise ValueError('Название: 1–100 символов')
    return {'title': title, 'message_text': validate_html(data.get('message_text'), 1024 if photo else 4096),
            'audience': chosen, 'reward': offer, 'photo_file_id': photo, 'buttons': clean_buttons}


def audience_rows(conn, audience):
    clauses = ['u.is_banned=0', 'u.telegram_id>0']
    params = []
    active = "EXISTS(SELECT 1 FROM vpn_keys k WHERE k.user_id=u.id AND datetime(k.expires_at)>datetime('now'))"
    segment = audience['segment']
    if segment == 'active':
        clauses.append(active)
    elif segment == 'expired':
        clauses.extend([f'NOT {active}', 'EXISTS(SELECT 1 FROM vpn_keys k WHERE k.user_id=u.id)'])
    elif segment == 'never_paid':
        clauses.append("NOT EXISTS(SELECT 1 FROM payments p WHERE p.user_id=u.id AND p.status IN ('paid','succeeded') AND p.payment_type IS NOT NULL AND p.payment_type!='trial')")
    elif segment == 'expiring':
        clauses.append("(SELECT MAX(datetime(k.expires_at)) FROM vpn_keys k WHERE k.user_id=u.id) BETWEEN datetime('now') AND datetime('now',?)")
        params.append(f"+{audience['expiring_days']} days")
    elif segment == 'selected':
        ids = audience['selected']
        if not ids:
            return []
        clauses.append('u.telegram_id IN (' + ','.join('?' for _ in ids) + ')')
        params.extend(ids)
    if audience['tariff_id']:
        clauses.append('EXISTS(SELECT 1 FROM vpn_keys k WHERE k.user_id=u.id AND k.tariff_id=?)')
        params.append(audience['tariff_id'])
    if audience['excluded']:
        clauses.append('u.telegram_id NOT IN (' + ','.join('?' for _ in audience['excluded']) + ')')
        params.extend(audience['excluded'])
    return [dict(r) for r in conn.execute('''SELECT u.id user_id,u.telegram_id,u.username,u.first_name,
        (SELECT k.id FROM vpn_keys k WHERE k.user_id=u.id ORDER BY datetime(k.expires_at) DESC,k.id DESC LIMIT 1) key_id
        FROM users u WHERE ''' + ' AND '.join(clauses) + ' ORDER BY u.id', params)]


def preview(data):
    payload = validate_payload(data)
    with get_db() as conn:
        rows = audience_rows(conn, payload['audience'])
    return {'count': len(rows), 'without_subscription': sum(not r['key_id'] for r in rows),
            'sample': [{k: r[k] for k in ('telegram_id', 'first_name', 'username')} for r in rows[:20]]}


def save(data, actor, campaign_id=None):
    payload = validate_payload(data)
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        promo = check_offer(conn, payload)
        if promo:
            payload['promo_snapshot'] = {k: promo[k] for k in ('code', 'discount_type', 'discount_percent', 'discount_rub', 'expires_at', 'max_uses')}
        rows = audience_rows(conn, payload['audience'])
        if campaign_id:
            old = conn.execute('SELECT status FROM admin_broadcasts WHERE id=?', (campaign_id,)).fetchone()
            if not old or old['status'] != 'draft':
                raise ValueError('Можно изменять только черновик')
            conn.execute('''UPDATE admin_broadcasts SET title=?,payload=?,revision=revision+1,
                tested_revision=NULL,tested_at=NULL,tested_admin=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                (payload['title'], json.dumps(payload, ensure_ascii=False), campaign_id))
            conn.execute('DELETE FROM admin_broadcast_recipients WHERE campaign_id=?', (campaign_id,))
        else:
            campaign_id = conn.execute('INSERT INTO admin_broadcasts(title,payload,created_by) VALUES(?,?,?)',
                (payload['title'], json.dumps(payload, ensure_ascii=False), str(actor))).lastrowid
        for row in rows:
            code = 'ARC_' + secrets.token_hex(6).upper() if payload['reward']['kind'] == 'personal_discount' else None
            conn.execute('''INSERT INTO admin_broadcast_recipients(campaign_id,user_id,telegram_id,key_id,promo_code)
                VALUES(?,?,?,?,?)''', (campaign_id, row['user_id'], row['telegram_id'], row['key_id'], code))
    return detail(campaign_id)


def detail(campaign_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM admin_broadcasts WHERE id=?', (campaign_id,)).fetchone()
        if not row:
            raise ValueError('Рассылка не найдена')
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        result['counts'] = {r['status']: r['n'] for r in conn.execute('''SELECT status,COUNT(*) n
            FROM admin_broadcast_recipients WHERE campaign_id=? GROUP BY status''', (campaign_id,))}
        result['total'] = sum(result['counts'].values())
        result['rewards'] = {r['reward_state']: r['n'] for r in conn.execute('''SELECT reward_state,COUNT(*) n
            FROM admin_broadcast_recipients WHERE campaign_id=? GROUP BY reward_state''', (campaign_id,))}
        result['without_subscription'] = conn.execute('SELECT COUNT(*) FROM admin_broadcast_recipients WHERE campaign_id=? AND key_id IS NULL', (campaign_id,)).fetchone()[0]
        result['errors'] = [dict(r) for r in conn.execute('''SELECT status,reward_state,error,COUNT(*) count
            FROM admin_broadcast_recipients WHERE campaign_id=? AND error IS NOT NULL GROUP BY status,reward_state,error LIMIT 20''', (campaign_id,))]
        return result


def listing():
    with get_db() as conn:
        ids = [r[0] for r in conn.execute("SELECT id FROM admin_broadcasts WHERE status != 'deleted' ORDER BY id DESC LIMIT 100")]
    return [detail(i) for i in ids]


def delete_draft(campaign_id):
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        changed = conn.execute("""UPDATE admin_broadcasts SET status='deleted',
            tested_revision=NULL,tested_admin=NULL,tested_at=NULL,
            updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='draft'""", (campaign_id,)).rowcount
        if not changed:
            raise ValueError('Можно удалять только существующий черновик')


def render(payload, recipient, *, promo=None):
    text = payload['message_text']
    reward = payload['reward']
    kind = reward['kind']
    if kind == 'days':
        if not recipient.get('key_id'):
            text += '\n\nБонусные дни доступны пользователям с существующей подпиской. У вашего аккаунта подписки пока нет.'
    elif kind != 'none':
        if kind == 'existing_promo':
            code = promo['code']
            value = promo['discount_percent'] if promo['discount_type'] == 'percent' else promo['discount_rub']
            unit = '%' if promo['discount_type'] == 'percent' else ' ₽'
            until = str(promo['expires_at'])[:10]
        else:
            code = recipient['promo_code'] if kind == 'personal_discount' else reward['code']
            value, unit = reward['discount_value'], '%' if reward['discount_type'] == 'percent' else ' ₽'
            until = f"{reward['duration_days']} дн. с запуска рассылки"
        text += f'\n\n🎟 Промокод: <code>{html.escape(code)}</code>\nСкидка: <b>{value}{unit}</b> · срок: {html.escape(until)}.'
        if kind == 'personal_discount':
            text += '\nТолько для вашего аккаунта, на одну покупку. Не суммируется с другими промокодами.'
    return validate_html(text, 1024 if payload['photo_file_id'] else 4096)


def check_offer(conn, payload):
    reward = payload['reward']
    if reward['kind'] == 'existing_promo':
        if conn.execute('SELECT 1 FROM broadcast_personal_promos WHERE promocode_id=?', (reward['promo_id'],)).fetchone():
            raise ValueError('Персональный промокод нельзя отправлять как общий')
        row = conn.execute('''SELECT *, (SELECT COUNT(*) FROM promocode_usage WHERE promocode_id=p.id) used_count
            FROM promocodes p WHERE p.id=? AND p.is_active=1 AND datetime(p.expires_at)>datetime('now')''', (reward['promo_id'],)).fetchone()
        if not row or row['used_count'] >= row['max_uses']:
            raise ValueError('Промокод недоступен или исчерпан')
        if payload.get('promo_snapshot') and any(row[k] != v for k, v in payload['promo_snapshot'].items()):
            raise ValueError('Промокод изменён: сохраните черновик и повторите тест')
        return dict(row)
    if reward['kind'] == 'new_promo' and conn.execute('SELECT 1 FROM promocodes WHERE code=?', (reward['code'],)).fetchone():
        raise ValueError('Такой промокод уже существует')
    return None


def test_samples(campaign_id):
    campaign = detail(campaign_id)
    if campaign['status'] != 'draft' or not campaign['total']:
        raise ValueError('Для теста нужен черновик с получателями')
    with get_db() as conn:
        promo = check_offer(conn, campaign['payload'])
        rows = [dict(r) for r in conn.execute('''SELECT * FROM admin_broadcast_recipients
            WHERE campaign_id=? ORDER BY key_id IS NULL,user_id LIMIT 1''', (campaign_id,))]
        if campaign['payload']['reward']['kind'] == 'days' and campaign['without_subscription'] and rows[0]['key_id']:
            rows += [dict(conn.execute('SELECT * FROM admin_broadcast_recipients WHERE campaign_id=? AND key_id IS NULL LIMIT 1', (campaign_id,)).fetchone())]
    return campaign, [render(campaign['payload'], row, promo=promo) for row in rows]


def mark_tested(campaign_id, revision, admin_id):
    with get_db() as conn:
        changed = conn.execute('''UPDATE admin_broadcasts SET tested_revision=?,tested_admin=?,tested_at=CURRENT_TIMESTAMP
            WHERE id=? AND revision=? AND status='draft' ''', (revision, admin_id, campaign_id, revision)).rowcount
        if not changed:
            raise ValueError('Черновик изменился: повторите тест')


def insert_promo(conn, code, reward, uses):
    promo_id = conn.execute('''INSERT INTO promocodes(code,discount_rub,discount_percent,discount_type,
        max_uses,expires_at,created_at,is_active) VALUES(?,?,?,?,?,datetime('now',?),CURRENT_TIMESTAMP,1)''',
        (code, reward['discount_value'] if reward['discount_type'] == 'fixed' else 0,
         reward['discount_value'] if reward['discount_type'] == 'percent' else 0,
         reward['discount_type'], uses, f"+{reward['duration_days']} days")).lastrowid
    conn.execute('INSERT INTO broadcast_campaign_promos VALUES(?)', (promo_id,))
    return promo_id


def start(campaign_id, revision, count):
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM admin_broadcasts WHERE id=?', (campaign_id,)).fetchone()
        if not row or row['status'] != 'draft' or row['revision'] != revision or row['tested_revision'] != revision:
            raise ValueError('Сначала отправьте тест текущей версии')
        total = conn.execute('SELECT COUNT(*) FROM admin_broadcast_recipients WHERE campaign_id=?', (campaign_id,)).fetchone()[0]
        if not total or total != count:
            raise ValueError('Подтвердите актуальное число получателей')
        payload = json.loads(row['payload'])
        promo = check_offer(conn, payload)
        for recipient in conn.execute('SELECT * FROM admin_broadcast_recipients WHERE campaign_id=?', (campaign_id,)):
            render(payload, dict(recipient), promo=promo)
        if payload['reward']['kind'] == 'new_promo':
            insert_promo(conn, payload['reward']['code'], payload['reward'], payload['reward']['max_uses'])
        conn.execute("UPDATE admin_broadcasts SET status='queued',started_at=CURRENT_TIMESTAMP WHERE id=?", (campaign_id,))
    return detail(campaign_id)


def stop(campaign_id):
    with get_db() as conn:
        conn.execute("UPDATE admin_broadcasts SET status='stopped',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('queued','running')", (campaign_id,))
    return detail(campaign_id)


def recover():
    with get_db() as conn:
        # Sending may have reached Telegram. Never blindly deliver it twice.
        conn.execute("UPDATE admin_broadcast_recipients SET status='uncertain',error='Отправка прервана: результат Telegram неизвестен' WHERE status='sending'")
        conn.execute("UPDATE admin_broadcasts SET status='queued' WHERE status='running'")


def next_recipient():
    with get_db() as conn:
        row = conn.execute('''SELECT r.*,b.payload FROM admin_broadcast_recipients r JOIN admin_broadcasts b ON b.id=r.campaign_id
            WHERE (b.status IN ('queued','running') AND r.status='pending' OR b.status='stopped' AND r.reward_state='sync_pending')
            AND (r.retry_at IS NULL OR datetime(r.retry_at)<=datetime('now')) ORDER BY r.campaign_id,r.user_id LIMIT 1''').fetchone()
        return dict(row) if row else None


def grant_once(recipient):
    cid, uid = recipient['campaign_id'], recipient['user_id']
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        campaign = conn.execute('SELECT status,payload FROM admin_broadcasts WHERE id=?', (cid,)).fetchone()
        current = dict(conn.execute('SELECT * FROM admin_broadcast_recipients WHERE campaign_id=? AND user_id=?', (cid, uid)).fetchone())
        if campaign['status'] == 'stopped' and current['reward_state'] == 'sync_pending':
            current['payload'] = json.loads(campaign['payload'])
            return current
        if campaign['status'] not in {'queued', 'running'}:
            return None
        if current['status'] != 'pending':
            return None
        if not conn.execute('SELECT 1 FROM users WHERE id=? AND telegram_id=? AND is_banned=0', (uid, current['telegram_id'])).fetchone():
            conn.execute("UPDATE admin_broadcast_recipients SET status='skipped',reward_state='excluded',error='Аккаунт исключён перед отправкой' WHERE campaign_id=? AND user_id=?", (cid, uid))
            return None
        conn.execute("UPDATE admin_broadcasts SET status='running',updated_at=CURRENT_TIMESTAMP WHERE id=?", (cid,))
        payload = json.loads(campaign['payload'])
        reward = payload['reward']
        if current['reward_state'] == 'pending':
            state = 'none'
            if reward['kind'] == 'days':
                # Pick current canonical key once, atomically with the extension.
                key = conn.execute('SELECT id FROM vpn_keys WHERE user_id=? ORDER BY datetime(expires_at) DESC,id DESC LIMIT 1', (uid,)).fetchone()
                if key:
                    current['key_id'] = key[0]
                    conn.execute("UPDATE vpn_keys SET expires_at=datetime(CASE WHEN datetime(expires_at)>datetime('now') THEN expires_at ELSE datetime('now') END,?),panel_disabled_at=NULL WHERE id=?", (f"+{reward['days']} days", key[0]))
                    state = 'sync_pending'
                else:
                    current['key_id'] = None
                    state = 'no_subscription'
            elif reward['kind'] == 'personal_discount':
                pid = insert_promo(conn, current['promo_code'], reward, 1)
                # Personal code expires with the campaign, not late retry time.
                conn.execute("UPDATE promocodes SET expires_at=datetime((SELECT started_at FROM admin_broadcasts WHERE id=?),?) WHERE id=?", (cid, f"+{reward['duration_days']} days", pid))
                conn.execute('INSERT INTO broadcast_personal_promos VALUES(?,?)', (pid, uid))
                current['promo_id'] = pid
                state = 'applied'
            elif reward['kind'] in {'new_promo', 'existing_promo'}:
                state = 'applied'
            conn.execute('UPDATE admin_broadcast_recipients SET key_id=?,promo_id=?,reward_state=? WHERE campaign_id=? AND user_id=?', (current['key_id'], current['promo_id'], state, cid, uid))
            current['reward_state'] = state
        current['payload'] = payload
        return current


def update_recipient(recipient, **changes):
    allowed = {'status', 'reward_state', 'attempts', 'retry_at', 'error', 'message_id', 'sent_at'}
    if not changes or not set(changes) <= allowed:
        raise ValueError('Invalid recipient update')
    with get_db() as conn:
        conn.execute('UPDATE admin_broadcast_recipients SET ' + ','.join(k + '=?' for k in changes) + ' WHERE campaign_id=? AND user_id=?', (*changes.values(), recipient['campaign_id'], recipient['user_id']))


def reserve_send(recipient):
    with get_db() as conn:
        return conn.execute("""UPDATE admin_broadcast_recipients SET status='sending',attempts=attempts+1
            WHERE campaign_id=? AND user_id=? AND status='pending'
            AND EXISTS(SELECT 1 FROM admin_broadcasts WHERE id=? AND status IN ('queued','running'))""",
            (recipient['campaign_id'], recipient['user_id'], recipient['campaign_id'])).rowcount == 1


def finish_ready():
    with get_db() as conn:
        conn.execute("""UPDATE admin_broadcasts SET status='completed',completed_at=CURRENT_TIMESTAMP
            WHERE status IN ('queued','running') AND NOT EXISTS(SELECT 1 FROM admin_broadcast_recipients r
                WHERE r.campaign_id=admin_broadcasts.id AND r.status IN ('pending','sending'))""")
