"""Owner-only API for campaign drafts, tests and explicit execution."""
from urllib.parse import urlsplit
from flask import jsonify, request

from database import db_admin_broadcasts as campaigns
from database.connection import get_db


def register_broadcast_routes(app, authorized, audit, executor, config):
    def denied():
        if not authorized('broadcasts.manage'):
            return jsonify(ok=False, error='Нет доступа к рассылкам'), 403
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(ok=False, error='Недопустимый источник запроса'), 403
        if request.method in {'POST', 'PUT'} and not request.is_json and request.endpoint != 'admin_broadcast_photo':
            return jsonify(ok=False, error='Ожидается JSON'), 415
        return None

    @app.after_request
    def broadcast_no_store(response):
        if request.path.startswith('/api/admin/broadcasts'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.route('/api/admin/broadcasts/options')
    def admin_broadcast_options():
        if (error := denied()) is not None:
            return error
        with get_db() as conn:
            tariffs = [dict(r) for r in conn.execute('SELECT id,name FROM tariffs ORDER BY id')]
            promos = [dict(r) for r in conn.execute('''SELECT id,code,discount_type,discount_percent,discount_rub,expires_at FROM promocodes p
                WHERE is_active=1 AND datetime(expires_at)>datetime('now') AND NOT EXISTS(
                    SELECT 1 FROM broadcast_personal_promos bp WHERE bp.promocode_id=p.id) ORDER BY id DESC LIMIT 100''')]
        admins = [int(i) for i in getattr(config, 'ADMIN_IDS', []) if int(i) > 0]
        test_admins = []
        with get_db() as conn:
            for n, admin_id in enumerate(admins):
                user = conn.execute('SELECT first_name,username FROM users WHERE telegram_id=?', (admin_id,)).fetchone()
                label = f'Администратор {n + 1}'
                if user:
                    label = str(user['first_name'] or label)
                    if user['username']:
                        label += f" · @{user['username']}"
                test_admins.append({'id': admin_id, 'label': label})
        return jsonify(ok=True, tariffs=tariffs, promocodes=promos,
            test_admins=test_admins)

    @app.route('/api/admin/broadcasts/users')
    def admin_broadcast_users():
        if (error := denied()) is not None:
            return error
        search = str(request.args.get('search') or '').strip()[:80]
        with get_db() as conn:
            conn.create_function('casefold', 1, lambda value: str(value or '').casefold())
            rows = conn.execute('''SELECT telegram_id,username,first_name FROM users
                WHERE is_banned=0 AND telegram_id>0 AND
                (instr(casefold(username),casefold(?))>0 OR instr(casefold(first_name),casefold(?))>0
                 OR instr(CAST(telegram_id AS TEXT),?)>0) ORDER BY id DESC LIMIT 30''', (search, search, search)).fetchall()
        return jsonify(ok=True, users=[dict(r) for r in rows])

    @app.route('/api/admin/broadcasts/preview', methods=['POST'])
    def admin_broadcast_preview():
        if (error := denied()) is not None:
            return error
        try:
            return jsonify(ok=True, **campaigns.preview(request.get_json()))
        except (ValueError, TypeError, AttributeError) as exc:
            return jsonify(ok=False, error=str(exc) if isinstance(exc, ValueError) else 'Некорректные поля'), 400

    @app.route('/api/admin/broadcasts', methods=['GET', 'POST'])
    @app.route('/api/admin/broadcasts/<int:campaign_id>', methods=['GET', 'PUT'])
    def admin_broadcast_campaigns(campaign_id=None):
        if (error := denied()) is not None:
            return error
        try:
            if request.method == 'GET':
                return jsonify(ok=True, **({'campaign': campaigns.detail(campaign_id)} if campaign_id else {'campaigns': campaigns.listing()}))
            result = campaigns.save(request.get_json(), 'owner', campaign_id)
            audit('broadcast.save', 'success', actor_id='owner', target_type='broadcast', target_id=str(result['id']))
            return jsonify(ok=True, campaign=result)
        except (ValueError, TypeError, AttributeError) as exc:
            return jsonify(ok=False, error=str(exc) if isinstance(exc, ValueError) else 'Некорректные поля'), 400

    @app.route('/api/admin/broadcasts/<int:campaign_id>', methods=['DELETE'])
    def admin_broadcast_delete(campaign_id):
        if (error := denied()) is not None:
            return error
        try:
            campaigns.delete_draft(campaign_id)
            audit('broadcast.delete', 'success', actor_id='owner', target_type='broadcast', target_id=str(campaign_id))
            return jsonify(ok=True)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 409

    @app.route('/api/admin/broadcasts/<int:campaign_id>/test', methods=['POST'])
    def admin_broadcast_test(campaign_id):
        if (error := denied()) is not None:
            return error
        try:
            target = int((request.get_json() or {}).get('admin_id') or 0)
            if target <= 0 or target not in getattr(config, 'ADMIN_IDS', []):
                raise ValueError('Выберите настроенного администратора')
            from aiogram import Bot
            from bot.services.admin_broadcast_worker import send_test

            async def deliver():
                bot = Bot(token=config.BOT_TOKEN)
                try:
                    return await send_test(bot, campaign_id, target)
                finally:
                    await bot.session.close()

            result = executor.run(deliver(), timeout=45)
            audit('broadcast.test', 'success', actor_id='owner', target_type='broadcast', target_id=str(campaign_id))
            return jsonify(ok=True, campaign=result)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400
        except Exception:
            return jsonify(ok=False, error='Тест не подтверждён. Проверьте, что администратор запустил бота, и повторите тест.'), 502

    @app.route('/api/admin/broadcasts/<int:campaign_id>/start', methods=['POST'])
    def admin_broadcast_start(campaign_id):
        if (error := denied()) is not None:
            return error
        try:
            body = request.get_json() or {}
            result = campaigns.start(campaign_id, int(body.get('revision') or 0), int(body.get('count') or 0))
            audit('broadcast.start', 'success', actor_id='owner', target_type='broadcast', target_id=str(campaign_id), metadata={'count': result['total']})
            return jsonify(ok=True, campaign=result)
        except (ValueError, TypeError) as exc:
            return jsonify(ok=False, error=str(exc) if isinstance(exc, ValueError) else 'Некорректное подтверждение'), 409

    @app.route('/api/admin/broadcasts/<int:campaign_id>/stop', methods=['POST'])
    def admin_broadcast_stop(campaign_id):
        if (error := denied()) is not None:
            return error
        try:
            result = campaigns.stop(campaign_id)
            audit('broadcast.stop', 'success', actor_id='owner', target_type='broadcast', target_id=str(campaign_id))
            return jsonify(ok=True, campaign=result)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 404

    @app.route('/api/admin/broadcasts/photo', methods=['POST'])
    def admin_broadcast_photo():
        if (error := denied()) is not None:
            return error
        if not request.headers.get('Origin'):
            return jsonify(ok=False, error='Требуется источник загрузки'), 403
        file = request.files.get('photo')
        if not file or file.mimetype not in {'image/jpeg', 'image/png', 'image/webp'}:
            return jsonify(ok=False, error='Выберите JPEG, PNG или WebP'), 400
        data = file.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            return jsonify(ok=False, error='Фотография должна быть меньше 5 МБ'), 400
        admins = getattr(config, 'ADMIN_IDS', [])
        if not admins:
            return jsonify(ok=False, error='Администратор Telegram не настроен'), 409
        # Send media to the configured admin, never to customers; file_id is then
        # reusable in the exact test/final payload.
        async def upload():
            from aiogram import Bot
            from aiogram.types import BufferedInputFile
            bot = Bot(token=config.BOT_TOKEN)
            try:
                message = await bot.send_photo(int(admins[0]), BufferedInputFile(data, filename='broadcast-photo'),
                    caption='Фото для черновика рассылки. Это загрузка, а не тест готового сообщения.', parse_mode=None)
                return message.photo[-1].file_id
            finally:
                await bot.session.close()
        try:
            return jsonify(ok=True, file_id=executor.run(upload(), timeout=45))
        except Exception:
            return jsonify(ok=False, error='Telegram не принял фотографию. Проверьте файл и доступ администратора к боту.'), 502
