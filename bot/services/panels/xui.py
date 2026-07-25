"""
Сервис для работы с API 3X-UI панели.

Обеспечивает:
- Авторизацию через сессии
- Управление клиентами (создание, удаление, обновление)
- Получение статистики трафика
- Управление inbound-подключениями
"""

import aiohttp
import asyncio
import logging
import json
import re
import uuid
import time
from typing import Optional, Dict, Any, List
from config import RETRY_CONFIG

logger = logging.getLogger(__name__)

XUI_HTTP_TOTAL_TIMEOUT_SECONDS = 6
XUI_HTTP_CONNECT_TIMEOUT_SECONDS = 3
XUI_HTTP_SOCK_READ_TIMEOUT_SECONDS = 5


def _as_obj(value):
    """
    Безопасно приводит поле панели (settings/streamSettings/...) к dict/list.

    3X-UI v3.0.0 отдаёт эти поля уже распарсенными (dict/list), тогда как старые
    версии отдавали их JSON-строкой. Помогает работать с обеими версиями.
    """
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (str, bytes, bytearray)):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {}
    return {} if value is None else value


from .base import BaseVPNClient, VPNAPIError
class XUIClient(BaseVPNClient):
    """
    Клиент для работы с API 3X-UI панели.
    
    Использует сессионную аутентификацию (cookie-based).
    ВАЖНО: Для 3X-UI куки могут быть привязаны к IP, поэтому используем unsafe=True для CookieJar.
    """
    
    def __init__(self, server: dict):
        """
        Инициализация клиента.
        
        Args:
            server: Словарь с данными сервера из БД
        """
        self.server = server
        self.host = server['host']
        self.port = server['port']
        self.protocol = server.get('protocol', 'https')
        # Гарантируем, что путь начинается со слеша, но НЕ заканчивается им
        # strip('/') убирает слеши и с начала, и с конца
        path = server.get('web_base_path', '').strip('/')
        # Теперь добавляем один слеш в начало (если путь не пустой)
        path = f"/{path}" if path else ""
        
        self.base_url = f"{self.protocol}://{self.host}:{self.port}{path}"
        # Origin (без пути) — нужен для прохождения Fetch-Metadata/Origin проверок
        # на write-эндпоинтах в свежих 3x-ui (иначе POST отбивается пустым 200).
        self.origin = f"{self.protocol}://{self.host}:{self.port}"

        self.session: Optional[aiohttp.ClientSession] = None
        self.is_authenticated = False
        self._csrf_token: Optional[str] = None  # 3x-ui v3.0.0+ CSRF-токен сессии
        # Версия client-API панели: "v2" (эндпоинты /panel/api/inbounds/*Client)
        # или "v3" (/panel/api/clients/*). Определяется лениво в _ensure_api_version
        # и кэшируется на время жизни клиента (внутри сессии не меняется).
        self._api_version: Optional[str] = None

        logger.debug(f"Инициализирован XUIClient для {server['name']}: {self.base_url}")
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Создаёт сессию если её нет."""
        if self.session is None or self.session.closed:
            # Unsafe=True важно для IP-адресов и самоподписанных сертификатов
            connector = aiohttp.TCPConnector(
                ssl=False,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            jar = aiohttp.CookieJar(unsafe=True)
            timeout = aiohttp.ClientTimeout(
                total=XUI_HTTP_TOTAL_TIMEOUT_SECONDS,
                connect=XUI_HTTP_CONNECT_TIMEOUT_SECONDS,
                sock_connect=XUI_HTTP_CONNECT_TIMEOUT_SECONDS,
                sock_read=XUI_HTTP_SOCK_READ_TIMEOUT_SECONDS,
            )
            self.session = aiohttp.ClientSession(connector=connector, cookie_jar=jar, timeout=timeout)
            self.is_authenticated = False
            logger.debug(f"Создана новая сессия для {self.server['name']}")
        return self.session
    
    async def _reset_session(self) -> None:
        """
        Сбрасывает текущую сессию.
        
        Вызывается при ошибках подключения для пересоздания сессии.
        """
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                logger.debug(f"Ошибка при закрытии сессии: {e}")
        self.session = None
        self.is_authenticated = False
        self._csrf_token = None
        logger.debug(f"Сессия сброшена для {self.server['name']}")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        retry: bool = True,
        log_error: bool = True,
        json_body: bool = False
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP-запрос к API.
        
        Args:
            method: HTTP метод (GET, POST)
            endpoint: Относительный путь (начинается с /panel/... или /login)
            data: Данные для POST запроса
            retry: Повторять ли при ошибках
            
        Returns:
            Ответ API в виде словаря
            
        Raises:
            VPNAPIError: При ошибке запроса
        """
        # URL = https://ip:port/secret_path/panel/...
        url = f"{self.base_url}{endpoint}"

        # Заголовки как у браузерного фронта панели. Свежие 3x-ui проверяют
        # Fetch-Metadata/Origin на write-эндпоинтах: без Sec-Fetch-Site/Origin
        # POST молча отбивается пустым 200 (запрос не доходит до обработчика).
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.origin,
            "Referer": f"{self.base_url}/panel/inbounds",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
        }

        attempts = RETRY_CONFIG["max_attempts"] if retry else 1
        delays = RETRY_CONFIG["delays"]

        for attempt in range(attempts):
            try:
                # Получаем актуальную сессию (важно, так как она может быть пересоздана в _reset_session)
                session = await self._ensure_session()

                # Если нужна авторизация и мы не авторизованы (и это не запрос логина)
                if not self.is_authenticated and endpoint != "/login":
                    await self.login()

                # v3.0.0: изменяющие запросы тоже требуют CSRF-токен сессии.
                req_headers = dict(headers)
                if self._csrf_token and endpoint != "/login":
                    req_headers["x-csrf-token"] = self._csrf_token

                logger.debug(f"API запрос: {method} {url}")

                # v2-write-эндпоинты (/panel/api/inbounds/*) биндят форму (ShouldBind),
                # поэтому тело шлём form-urlencoded. v3-эндпоинты (/panel/api/clients/*)
                # ждут JSON (фронт шлёт с Content-Type: application/json) — для них
                # вызывающий код передаёт json_body=True.
                if method.upper() == "POST" and isinstance(data, dict) and not json_body:
                    req_kwargs = {"data": data}
                else:
                    req_kwargs = {"json": data} if data is not None else {}

                async with session.request(method, url, headers=req_headers, **req_kwargs) as response:
                    text = await response.text()
                    
                    # Обработка статусов
                    if response.status == 200:

                        # Некоторые версии 2.x-ui возвращают пустой ответ при успешном POST
                        if not text.strip():
                            logger.info("Панель вернула пустой 200, считаем успешным ответом")
                            return {"success": True}
                        
                        try:
                            result = json.loads(text)
                            if result.get("success"):
                                return result
                            
                            # Бывает success=False но есть msg
                            if "msg" in result and not result["success"]:
                                msg = result["msg"].lower()
                                # Проверяем на признаки истечения сессии
                                if any(x in msg for x in ["login", "auth", "session", "token"]):
                                    logger.warning(f"Сессия возможно истекла (msg='{result['msg']}'), пересоздаём...")
                                    await self._reset_session()
                                    if attempt < attempts - 1:
                                        # Сессия будет пересоздана при следующем запросе
                                        continue
                                        
                                raise VPNAPIError(result["msg"])
                            return result
                        except json.JSONDecodeError:
                            # Иногда возвращает HTML при редиректе на логин
                            if "login" in text.lower():
                                logger.warning("Сессия истекла (редирект на логин), пересоздаём...")
                                await self._reset_session()
                                if attempt < attempts - 1:
                                    # Сессия будет пересоздана при следующем запросе
                                    continue
                            logger.error(f"Невалидный JSON: {text[:100]}")
                            raise VPNAPIError("Некорректный ответ сервера")
                    elif response.status == 404:
                         # Некоторые версии X-UI возвращают 404 если сессия истекла
                         # Пытаемся пересоздать сессию
                         logger.warning(f"HTTP 404 (Endpoint not found) для {url}, сессия возможно истекла. Попытка {attempt+1}/{attempts}")
                         await self._reset_session()
                         if attempt < attempts - 1:
                             continue
                         
                         if log_error:
                             logger.error(f"Endpoint not found после {attempts} попыток: {url}")
                         raise VPNAPIError("Ошибка API: Метод не найден (404). Проверьте настройки сервера.")
                    elif response.status == 401:
                        logger.warning("HTTP 401, пересоздаём сессию...")
                        await self._reset_session()
                        if attempt < attempts - 1:
                            continue
                    elif response.status == 403:
                        # v3.0.0: вероятно протух/не принят CSRF-токен — сбрасываем
                        # сессию (это обнулит токен) и повторяем: при следующем
                        # запросе произойдёт login() с получением свежего токена.
                        logger.warning(f"HTTP 403 для {url}, обновляем CSRF/сессию. Попытка {attempt+1}/{attempts}")
                        await self._reset_session()
                        if attempt < attempts - 1:
                            continue

                    raise VPNAPIError(f"HTTP {response.status}: {text[:100]}")
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Ошибка подключения (попытка {attempt+1}): {e}")
                # Сбрасываем сессию при ошибках подключения, чтобы пересоздать её
                await self._reset_session()
                if attempt < attempts - 1:
                    await asyncio.sleep(delays[attempt])
                else:
                    raise VPNAPIError(f"Ошибка подключения: {e}")
            except VPNAPIError:
                raise
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                raise VPNAPIError(f"Неожиданная ошибка: {e}")
        
        raise VPNAPIError("Превышено количество попыток")

    async def _fetch_csrf_token(self, session: aiohttp.ClientSession) -> Optional[str]:
        """
        Получает CSRF-токен для логина (3x-ui v3.0.0+).

        В v3 эндпоинт /login защищён CSRF: нужно сделать GET в рамках той же
        сессии (кука сохраняется в cookie_jar) и передать токен заголовком
        x-csrf-token. На старых версиях эндпоинта/мета-тега нет — возвращаем None
        и логинимся как раньше (обратная совместимость).

        Источники токена (по порядку): GET /csrf-token (plain или JSON),
        затем <meta name="csrf-token" content="..."> на корневой странице панели.

        ВАЖНО: на v2.x эндпоинта /csrf-token нет, и панель может отдать SPA-HTML
        со статусом 200. Поэтому принимаем значение, ТОЛЬКО если оно похоже на
        токен (короткое, без HTML/пробелов/переносов) — иначе токен остаётся None
        и запросы идут без x-csrf-token, как на старых версиях.
        """
        def _valid(t):
            return bool(t) and len(t) <= 256 and re.fullmatch(r"[A-Za-z0-9_\-+/=.]+", t) is not None

        # 1) Специальный эндпоинт v3
        try:
            async with session.get(f"{self.base_url}/csrf-token") as r:
                if r.status == 200:
                    body = (await r.text()).strip()
                    if body:
                        if body.startswith("{"):
                            try:
                                obj = json.loads(body)
                                token = obj.get("token") or obj.get("obj") or obj.get("csrf") or ""
                            except json.JSONDecodeError:
                                token = ""
                        else:
                            token = body
                        if _valid(token):
                            self._csrf_token = token
                            return token
        except Exception as e:
            logger.debug(f"csrf-token endpoint недоступен: {e}")

        # 2) Фолбэк: meta-тег на корневой странице панели
        try:
            async with session.get(f"{self.base_url}/") as r:
                if r.status == 200:
                    html = await r.text()
                    m = re.search(r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', html)
                    if m and _valid(m.group(1)):
                        self._csrf_token = m.group(1)
                        return self._csrf_token
        except Exception as e:
            logger.debug(f"не удалось получить csrf-token из HTML: {e}")

        return None

    async def login(self) -> bool:
        """
        Авторизация в панели 3X-UI.

        Returns:
            True при успешной авторизации

        Raises:
            VPNAPIError: При ошибке авторизации
        """
        logger.debug(f"Авторизация на {self.server['name']}...")

        session = await self._ensure_session()
        url = f"{self.base_url}/login"

        # Браузерные заголовки + CSRF (для v3). Логин работает и без них, но шлём
        # их единообразно, чтобы пройти возможные Origin/Fetch-Metadata проверки.
        login_headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.origin,
            "Referer": f"{self.base_url}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
        }
        csrf_token = await self._fetch_csrf_token(session)
        if csrf_token:
            login_headers["x-csrf-token"] = csrf_token
            logger.debug("CSRF-токен получен для логина")

        try:
            async with session.post(url, json={
                "username": self.server["login"],
                "password": self.server["password"]
            }, headers=login_headers) as resp:
                text = await resp.text()
                if resp.status == 200:
                    data = json.loads(text)
                    if data.get("success"):
                        self.is_authenticated = True
                        logger.debug("Успешная авторизация в XUI")
                        return True
                    else:
                        raise VPNAPIError(f"Ошибка логина: {data.get('msg')}")
                if resp.status == 404:
                    raise VPNAPIError(f"Панель недоступна по пути {self.server['web_base_path']}")
                else:
                    raise VPNAPIError(f"HTTP {resp.status} при логине")
        except aiohttp.ClientConnectorError:
            raise VPNAPIError(f"Не удалось подключиться к {self.server.get('protocol', 'https')}://{self.server['host']}:{self.server['port']}")
        except asyncio.TimeoutError:
            raise VPNAPIError("Таймаут при логине")
        except json.JSONDecodeError:
            raise VPNAPIError("Некорректный ответ при логине")

    async def get_inbounds(self) -> List[Dict[str, Any]]:
        """
        Получает список подключений (Inbounds).
        
        Returns:
            Список inbound-подключений
        """
        result = await self._request("GET", "/panel/api/inbounds/list")
        return result.get("obj", [])

    # ========================================================================
    # Версия client-API (v2 inbounds/*Client  vs  v3 clients/*) и v3-хелперы
    # ========================================================================

    async def _ensure_api_version(self) -> str:
        """
        Определяет и кэширует версию client-API панели ("v2" | "v3").

        v3.0.0 перенёс операции с клиентами на /panel/api/clients/* и добавил
        GET /panel/api/inbounds/list/slim (в v2 его нет → 404). По нему и детектим.
        Можно форсировать через config.XUI_FORCE_API_VERSION ("v2"|"v3").
        Read-путь (inbounds/list + settings.clients) одинаков в обеих версиях,
        поэтому версия нужна только для write-операций.
        """
        if self._api_version:
            return self._api_version

        forced = None
        try:
            import config
            forced = getattr(config, "XUI_FORCE_API_VERSION", None)
        except Exception:
            forced = None
        if forced in ("v2", "v3"):
            self._api_version = forced
            return forced

        try:
            r = await self._request("GET", "/panel/api/inbounds/list/slim", retry=False, log_error=False)
            self._api_version = "v3" if isinstance(r, dict) and r.get("success") else "v2"
        except VPNAPIError as e:
            # Кэшируем v2 только при явном 404 (эндпоинта нет → старая панель).
            # При неоднозначной ошибке (сеть/логин) НЕ кэшируем — переопределим
            # на следующем вызове, чтобы не залипнуть в неверной версии.
            msg = str(e).lower()
            if "404" in msg or "не найден" in msg:
                self._api_version = "v2"
            else:
                logger.warning("Не удалось определить версию API панели (%s); временно считаем v2", e)
                return "v2"
        logger.info("API панели %s определён как %s", self.server.get("name", "?"), self._api_version)
        return self._api_version

    @staticmethod
    def _to_int_tgid(tg_id) -> int:
        """tgId в v3 — целое >= 0; пустое/нечисловое → 0."""
        s = str(tg_id or "").strip()
        return int(s) if s.isdigit() else 0

    async def _v3_get_client(self, email: str) -> Optional[Dict[str, Any]]:
        """Читает объединённого клиента v3 (GET /panel/api/clients/get/{email})."""
        import urllib.parse
        enc = urllib.parse.quote(email, safe='')
        try:
            r = await self._request("GET", f"/panel/api/clients/get/{enc}", retry=False, log_error=False)
            obj = r.get("obj") if isinstance(r, dict) else None
            return obj if isinstance(obj, dict) else None
        except VPNAPIError:
            return None

    def _v3_client_body(
        self,
        *,
        email: str,
        secret: str,
        sub_id: str,
        total_bytes: int,
        expiry_ms: int,
        limit_ip: int,
        enable: bool,
        tg_id,
        inbound_ids: List[int],
        flow: str = "",
    ) -> Dict[str, Any]:
        """
        Собирает тело клиента для v3 (clients/add|update). Один клиент привязан к
        нескольким inbound через inboundIds. Секрет кладём и в uuid (для VLESS), и
        в password (для Hysteria2/Trojan) — так одна запись обслуживает все inbound
        под единым секретом (как зеркалирование в v2).

        Возвращает тело клиента (без inboundIds) — вызывающий код заворачивает в
        {"client": ..., "inboundIds": ...} для clients/add, либо шлёт как есть
        для clients/update/{email}.
        """
        return {
            "email": email,
            "uuid": secret,
            "password": secret,
            "flow": flow or "",
            "limitIp": limit_ip,
            "totalGB": total_bytes,
            "expiryTime": expiry_ms,
            "enable": enable,
            "tgId": self._to_int_tgid(tg_id),
            "subId": sub_id,
            "comment": "",
            "reset": 0,
        }

    async def _v3_post_client(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """POST на v3 client-эндпоинт с JSON-телом."""
        return await self._request("POST", endpoint, data=body, json_body=True)

    async def _v3_update_fields(self, email: str, **changes) -> bool:
        """
        Обновляет клиента v3: читает текущего, применяет changes, шлёт
        POST /panel/api/clients/update/{email} полным объектом (иначе панель
        затрёт незаданные поля — в т.ч. inboundIds).
        """
        import urllib.parse
        cur = await self._v3_get_client(email)
        if not cur:
            raise VPNAPIError(f"Клиент {email} не найден на панели (v3)")
        body = {
            "email": cur.get("email", email),
            "uuid": cur.get("uuid", ""),
            "password": cur.get("password", ""),
            "flow": cur.get("flow", ""),
            "limitIp": cur.get("limitIp", 0),
            "totalGB": cur.get("totalGB", 0),
            "expiryTime": cur.get("expiryTime", 0),
            "enable": cur.get("enable", True),
            "tgId": self._to_int_tgid(cur.get("tgId", 0)),
            "subId": cur.get("subId", ""),
            "comment": cur.get("comment", ""),
            "reset": cur.get("reset", 0),
            "inboundIds": cur.get("inboundIds") or [],
        }
        body.update(changes)
        enc = urllib.parse.quote(email, safe='')
        # 3x-ui v3 expects client fields at the JSON root on update. The
        # nested {"client": ...} shape belongs to clients/add and is rejected
        # here with "client email is required".
        await self._v3_post_client(f"/panel/api/clients/update/{enc}", body)
        return True

    async def _v3_list_clients(self) -> List[Dict[str, Any]]:
        """Возвращает всех клиентов панели v3 (GET /panel/api/clients/list)."""
        try:
            r = await self._request("GET", "/panel/api/clients/list", retry=False, log_error=False)
            obj = r.get("obj") if isinstance(r, dict) else None
            return obj if isinstance(obj, list) else []
        except VPNAPIError:
            return []

    def _v3_client_as_settings_entry(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """
        Приводит клиента из clients/list (поля v3: uuid/password/subId/flow/...) к
        форме записи settings.clients, которую понимает _build_client_config
        (ожидает id=uuid для VLESS/VMess, password для остальных).
        """
        return {
            "id": c.get("uuid", ""),
            "password": c.get("password", ""),
            "email": c.get("email", ""),
            "subId": c.get("subId", ""),
            "flow": c.get("flow", ""),
            "security": c.get("security", "auto"),
        }

    async def _v3_configs_by_inbound(
        self, emails: set, multi: bool
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Собирает конфиги для v3 через clients/list + inboundIds.

        multi=True  → по конфигу на КАЖДЫЙ привязанный inbound (для подписки).
        multi=False → один конфig (VLESS-приоритет) на email.
        Возвращает {email: [config, ...]}.
        """
        inbounds = await self.get_inbounds()
        if not multi:
            inbounds = self._sort_inbounds_vless_first(inbounds)
        ib_by_id = {ib.get("id"): ib for ib in inbounds}
        out: Dict[str, List[Dict[str, Any]]] = {e: [] for e in emails}

        for c in await self._v3_list_clients():
            email = c.get("email", "")
            if email not in emails:
                continue
            entry = self._v3_client_as_settings_entry(c)
            # inboundIds в порядке VLESS-first (как отсортированы inbounds)
            ordered_ids = [ib.get("id") for ib in inbounds if ib.get("id") in set(c.get("inboundIds") or [])]
            for ib_id in ordered_ids:
                inbound = ib_by_id.get(ib_id)
                if not inbound or inbound.get("protocol") not in self.SUPPORTED_PROTOCOLS:
                    continue
                settings = _as_obj(inbound.get("settings", "{}"))
                out[email].append(self._build_client_config(inbound, settings, entry))
                if not multi:
                    break
        return {e: cfgs for e, cfgs in out.items() if cfgs}

    async def _v3_attach(self, email: str, inbound_ids: List[int]) -> None:
        """
        Привязывает клиента к указанным inbound (v3: POST clients/{email}/attach).

        В v3 `clients/update` меняет только поля клиента и НЕ меняет привязку к
        inbound — для добавления в новый inbound нужен отдельный attach. Тело —
        JSON {inboundIds:[...]}.
        """
        if not inbound_ids:
            return
        import urllib.parse
        enc = urllib.parse.quote(email, safe='')
        await self._v3_post_client(
            f"/panel/api/clients/{enc}/attach", {"inboundIds": list(inbound_ids)}
        )

    async def _v3_email_for_secret(self, secret: str) -> Optional[str]:
        """Находит email клиента по секрету (id/password) через inbounds/list."""
        try:
            for ib in await self.get_inbounds():
                settings = _as_obj(ib.get("settings", "{}"))
                for c in (settings.get("clients") or []):
                    if c.get("id") == secret or c.get("password") == secret:
                        return c.get("email")
        except Exception as e:
            logger.debug("Не удалось сопоставить секрет с email (v3): %s", e)
        return None

    async def _v3_provision_all(
        self,
        *,
        email: str,
        secret: str,
        sub_id: str,
        total_bytes: int,
        expiry_ms: int,
        limit_ip: int,
        enable: bool,
        tg_id,
    ) -> Dict[str, Any]:
        """
        v3-провижининг: один клиент во ВСЕ поддерживаемые inbound одним вызовом
        (нативный inboundIds). Если клиент с таким email уже есть — upsert через
        update (сохраняем его uuid/subId, доклеиваем недостающие inbound).
        """
        inbounds = await self.get_inbounds()
        if not inbounds:
            raise VPNAPIError("На сервере нет ни одного inbound")
        supported = [ib for ib in inbounds if ib.get("protocol") in self.SUPPORTED_PROTOCOLS]
        if not supported:
            raise VPNAPIError("На сервере нет поддерживаемых inbound")
        supported_ids = [ib["id"] for ib in supported]

        flow = ""
        primary_inbound_id: Optional[int] = None
        for ib in supported:
            if ib.get("protocol") == "vless":
                flow = self._compute_flow_from_inbound(ib)
                primary_inbound_id = ib["id"]
                break
        if primary_inbound_id is None:
            primary_inbound_id = supported_ids[0]

        existing = await self._v3_get_client(email)
        if existing:
            secret = existing.get("uuid") or existing.get("password") or secret
            sub_id = existing.get("subId") or sub_id
            current_ids = set(existing.get("inboundIds") or [])
            target_ids = sorted(current_ids | set(supported_ids))
            # update меняет только поля; привязку к НОВЫМ inbound делает attach.
            body = self._v3_client_body(
                email=email, secret=secret, sub_id=sub_id, total_bytes=total_bytes,
                expiry_ms=expiry_ms, limit_ip=limit_ip, enable=enable, tg_id=tg_id,
                inbound_ids=target_ids, flow=flow,
            )
            import urllib.parse
            enc = urllib.parse.quote(email, safe='')
            await self._v3_post_client(f"/panel/api/clients/update/{enc}", body)
            missing = [i for i in supported_ids if i not in current_ids]
            if missing:
                await self._v3_attach(email, missing)
            provisioned = target_ids
            logger.info("Клиент %s обновлён в v3 (inboundIds=%s, доклеено=%s)", email, target_ids, missing)
        else:
            body = self._v3_client_body(
                email=email, secret=secret, sub_id=sub_id, total_bytes=total_bytes,
                expiry_ms=expiry_ms, limit_ip=limit_ip, enable=enable, tg_id=tg_id,
                inbound_ids=supported_ids, flow=flow,
            )
            await self._v3_post_client("/panel/api/clients/add", {"client": body, "inboundIds": supported_ids})
            provisioned = supported_ids
            logger.info("Клиент %s создан в v3 (inboundIds=%s)", email, supported_ids)

        return {
            "uuid": secret,
            "email": email,
            "sub_id": sub_id,
            "primary_inbound_id": primary_inbound_id,
            "inbound_ids": provisioned,
        }

    async def get_server_status(self) -> Dict[str, Any]:
        """
        Получает статус сервера (CPU, память, uptime).
        
        Returns:
            Словарь со статусом сервера
        """
        try:
            result = await self._request("GET", "/panel/api/server/status")
            return result.get("obj", {})
        except VPNAPIError:
            # Некоторые версии 3X-UI не имеют этого endpoint
            return {}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику сервера.
        
        Returns:
            Словарь со статистикой:
            - total_clients: Общее количество клиентов
            - active_clients: Количество активных клиентов (enable=True)
            - total_traffic_bytes: Общий трафик (up + down)
            - cpu_percent: Загрузка CPU (если доступно)
            - online: True если сервер доступен
        """
        try:
            inbounds = await self.get_inbounds()
            
            total_clients = 0
            active_clients = 0
            total_traffic = 0
            
            for inbound in inbounds:
                # Парсим настройки клиентов
                settings_str = inbound.get("settings", "{}")
                try:
                    settings = _as_obj(settings_str)
                    clients = (settings.get("clients") or [])
                    total_clients += len(clients)
                    
                    for client in clients:
                        if client.get("enable", True):
                            active_clients += 1
                except json.JSONDecodeError:
                    pass
                
                # Трафик inbound
                total_traffic += inbound.get("up", 0)
                total_traffic += inbound.get("down", 0)
            
            # Пробуем получить статус сервера (CPU)
            cpu_percent = None
            try:
                status = await self.get_server_status()
                if status:
                    raw_cpu = status.get("cpu")
                    if raw_cpu is not None:
                        try:
                            cpu_percent = int(float(raw_cpu))
                        except (ValueError, TypeError):
                            pass
            except VPNAPIError:
                pass
            
            return {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "online_clients": await self.get_online_clients_count(),
                "total_traffic_bytes": total_traffic,
                "cpu_percent": cpu_percent,
                "online": True
            }
            
        except VPNAPIError as e:
            logger.warning(f"Ошибка получения статистики: {e}")
            return {
                "total_clients": 0,
                "active_clients": 0,
                "online_clients": 0,
                "total_traffic_bytes": 0,
                "cpu_percent": None,
                "online": False,
                "error": str(e)
            }

    async def get_online_clients_count(self) -> int:
        """
        Получает количество пользователей онлайн.

        Returns:
            Количество пользователей онлайн
        """
        try:
            # v3 перенёс онлайны в /panel/api/clients/onlines (в v2 — inbounds/onlines)
            ep = "/panel/api/clients/onlines" if await self._ensure_api_version() == "v3" else "/panel/api/inbounds/onlines"
            response = await self._request("POST", ep, retry=False, log_error=False)
            if response.get("success") and response.get("obj"):
                return len(response["obj"])
        except VPNAPIError:
            pass
        except Exception as e:
            logger.debug(f"Ошибка получения online пользователей: {e}")
        return 0

    async def get_online_emails(self) -> set:
        """
        Возвращает множество email клиентов, которые сейчас онлайн.

        Returns:
            set[str] — email'ы онлайн-клиентов (пусто при ошибке/отсутствии данных)
        """
        try:
            ep = "/panel/api/clients/onlines" if await self._ensure_api_version() == "v3" else "/panel/api/inbounds/onlines"
            response = await self._request("POST", ep, retry=False, log_error=False)
            obj = response.get("obj") if response.get("success") else None
            if obj:
                return {str(e) for e in obj}
        except VPNAPIError:
            pass
        except Exception as e:
            logger.debug(f"Ошибка получения online email'ов: {e}")
        return set()

    async def get_client_ips(self, email: str) -> list:
        """
        Возвращает список IP-адресов, с которых клиент подключён (≈ устройства).

        Зависит от логирования IP в 3X-UI (включается при limitIp). Если данных
        нет — возвращает пустой список (best-effort, не бросает исключение).

        Args:
            email: Email клиента на панели

        Returns:
            list[str] — уникальные IP клиента
        """
        try:
            import urllib.parse as _up
            if await self._ensure_api_version() == "v3":
                ip_ep = f"/panel/api/clients/ips/{_up.quote(email, safe='')}"
            else:
                ip_ep = f"/panel/api/inbounds/clientIps/{email}"
            response = await self._request("POST", ip_ep, retry=False, log_error=False)
            if not response.get("success"):
                return []
            obj = response.get("obj")
            # 3X-UI отдаёт либо строку "No IP Record" / список, либо JSON-строку со списком.
            if not obj or (isinstance(obj, str) and "no ip" in obj.lower()):
                return []
            if isinstance(obj, str):
                import json as _json
                try:
                    parsed = _json.loads(obj)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except (ValueError, TypeError):
                    # Может прийти строка вида "ip1,ip2"
                    return [p.strip() for p in obj.replace("\n", ",").split(",") if p.strip()]
            if isinstance(obj, list):
                return [str(x) for x in obj]
        except VPNAPIError:
            pass
        except Exception as e:
            logger.debug(f"Ошибка получения IP клиента {email}: {e}")
        return []

    # Протоколы, для которых мы умеем строить клиента и ссылку подписки.
    SUPPORTED_PROTOCOLS = ("vless", "vmess", "trojan", "shadowsocks", "hysteria2", "hysteria")

    @staticmethod
    def _build_client_entry(
        protocol: str,
        secret: str,
        email: str,
        sub_id: str,
        total_bytes: int,
        expiry_ms: int,
        limit_ip: int,
        enable: bool,
        tg_id: str,
        flow: str = "",
    ) -> Dict[str, Any]:
        """
        Собирает запись клиента (settings.clients[]) под конкретный протокол inbound.

        Один и тот же `secret` (uuid-строка) используется как id (VLESS/VMess) или
        как password (Trojan/Shadowsocks/Hysteria2) — это позволяет хранить один
        client_uuid в БД и при этом зеркалировать клиента во все inbound сервера.
        """
        entry = {
            "email": email,
            "limitIp": limit_ip,
            "totalGB": total_bytes,
            "expiryTime": expiry_ms,
            "enable": enable,
            "tgId": tg_id,
            "subId": sub_id,
            "reset": 0,
        }
        if protocol == "trojan":
            entry["password"] = secret
            entry["flow"] = flow
        elif protocol == "shadowsocks":
            # Shadowsocks — клиент наследует method из inbound
            entry["password"] = secret
            entry["method"] = ""
        elif protocol in ("hysteria2", "hysteria"):
            # Hysteria2 — аутентификация по password
            entry["password"] = secret
        else:
            # VLESS / VMess — используют id (UUID)
            entry["id"] = secret
            entry["flow"] = flow
        return entry

    @staticmethod
    def _compute_flow_from_inbound(inbound: Dict[str, Any]) -> str:
        """
        Возвращает flow для inbound (без дополнительного запроса к панели).
        Flow = 'xtls-rprx-vision' только для VLESS + TCP + (Reality | TLS).
        """
        if inbound.get("protocol", "") != "vless":
            return ""
        stream = _as_obj(inbound.get("streamSettings", "{}"))
        network = stream.get("network", "tcp")
        security = stream.get("security", "none")
        if network == "tcp" and security in ("reality", "tls"):
            return "xtls-rprx-vision"
        return ""

    async def provision_client_all_inbounds(
        self,
        email: str,
        total_gb: int = 0,
        expire_days: int = 30,
        limit_ip: int = 1,
        enable: bool = True,
        tg_id: str = "",
        expire_minutes: Optional[int] = None,
        secret: Optional[str] = None,
        sub_id: Optional[str] = None,
        only_missing: bool = False,
    ) -> Dict[str, Any]:
        """
        Создаёт (зеркалирует) клиента во ВСЕХ поддерживаемых inbound сервера под
        одним секретом/subId/email. Так одна подписка отдаёт по конфигу на каждый
        inbound (VLESS, Hysteria2, ...), а в БД хранится один client_uuid.

        Args:
            email: уникальный идентификатор клиента на панели
            total_gb: лимит трафика в ГБ (0 = безлимит)
            expire_days: срок в днях (игнорируется, если задан expire_minutes)
            limit_ip: лимит устройств
            enable: включён ли клиент
            tg_id: Telegram ID
            expire_minutes: срок в минутах (для тестовых ключей)
            secret: переиспользовать существующий секрет (uuid/password). По
                умолчанию генерируется новый.
            sub_id: переиспользовать существующий subId. По умолчанию новый.
            only_missing: добавлять только в те inbound, где клиента с таким email
                ещё нет (для бэкфилла — не трогаем рабочие inbound).

        Returns:
            {uuid, email, sub_id, primary_inbound_id, inbound_ids: [...]}

        Raises:
            VPNAPIError: если не удалось создать клиента ни в одном inbound
        """
        if expire_minutes is None and expire_days <= 0:
            raise ValueError("Срок действия ключа должен быть больше 0 дней")

        secret = secret or str(uuid.uuid4())
        sub_id = sub_id or uuid.uuid4().hex

        if expire_minutes is not None:
            expiry_ms = int((time.time() + expire_minutes * 60) * 1000)
        elif expire_days > 0:
            expiry_ms = int((time.time() + expire_days * 86400) * 1000)
        else:
            expiry_ms = 0

        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0

        # v3: один клиент во все inbound нативно (inboundIds), без ручного цикла.
        if await self._ensure_api_version() == "v3":
            return await self._v3_provision_all(
                email=email, secret=secret, sub_id=sub_id, total_bytes=total_bytes,
                expiry_ms=expiry_ms, limit_ip=limit_ip, enable=enable, tg_id=tg_id,
            )

        inbounds = await self.get_inbounds()
        if not inbounds:
            raise VPNAPIError("На сервере нет ни одного inbound")

        primary_inbound_id: Optional[int] = None
        provisioned: List[int] = []

        for inbound in inbounds:
            ib_id = inbound.get("id")
            protocol = inbound.get("protocol", "")
            if protocol not in self.SUPPORTED_PROTOCOLS:
                logger.debug("Пропускаем inbound %s: протокол %s не поддерживается", ib_id, protocol)
                continue

            settings = _as_obj(inbound.get("settings", "{}"))
            existing_clients = settings.get("clients") or []
            existing_id = None
            for c in existing_clients:
                if c.get("email") == email:
                    existing_id = c.get("id") or c.get("password")
                    break

            if existing_id and only_missing:
                # Бэкфилл: клиент уже есть в этом inbound — не трогаем.
                provisioned.append(ib_id)
                if protocol == "vless" and primary_inbound_id is None:
                    primary_inbound_id = ib_id
                continue

            if existing_id:
                try:
                    await self.delete_client(ib_id, existing_id)
                except Exception as e:
                    logger.error("Не удалось удалить существующего клиента %s в inbound %s: %s", email, ib_id, e)

            ib_flow = self._compute_flow_from_inbound(inbound)
            entry = self._build_client_entry(
                protocol=protocol,
                secret=secret,
                email=email,
                sub_id=sub_id,
                total_bytes=total_bytes,
                expiry_ms=expiry_ms,
                limit_ip=limit_ip,
                enable=enable,
                tg_id=tg_id,
                flow=ib_flow,
            )
            client_data = {"id": ib_id, "settings": json.dumps({"clients": [entry]})}
            try:
                resp = await self._request("POST", "/panel/api/inbounds/addClient", data=client_data)
                if not resp.get("success", True):
                    logger.error("Ошибка создания клиента %s в inbound %s: %s", email, ib_id, resp.get("msg"))
                    continue
                provisioned.append(ib_id)
                if protocol == "vless" and primary_inbound_id is None:
                    primary_inbound_id = ib_id
                logger.info("Клиент %s создан в inbound %s (%s)", email, ib_id, protocol)
            except Exception as e:
                logger.error("Не удалось создать клиента %s в inbound %s: %s", email, ib_id, e)

        if not provisioned:
            raise VPNAPIError(f"Не удалось создать клиента {email} ни в одном inbound")

        if primary_inbound_id is None:
            primary_inbound_id = provisioned[0]

        return {
            "uuid": secret,
            "email": email,
            "sub_id": sub_id,
            "primary_inbound_id": primary_inbound_id,
            "inbound_ids": provisioned,
        }

    async def add_client(
        self,
        inbound_id: int,
        email: str,
        total_gb: int = 0,
        expire_days: int = 30,
        limit_ip: int = 1,
        enable: bool = True,
        tg_id: str = "",
        flow: str = "",
        expire_minutes: int = None
    ) -> Dict[str, Any]:
        """
        Добавляет клиента в inbound.
        
        Args:
            inbound_id: ID inbound-подключения
            email: Уникальный идентификатор клиента (используем user_{id})
            total_gb: Лимит трафика в ГБ (0 = без лимита)
            expire_days: Срок действия в днях (0 = бессрочно, игнорируется если указан expire_minutes)
            limit_ip: Ограничение по IP (1 = 1 устройство)
            enable: Активен ли клиент
            tg_id: Telegram ID для уведомлений панели
            flow: Параметр flow (напр. 'xtls-rprx-vision' для VLESS Reality/TLS TCP)
            expire_minutes: Срок действия в минутах (для тестовых ключей, опционально)
            
        Returns:
            Словарь с данными созданного клиента
            
        Raises:
            ValueError: Если expire_days <= 0 и expire_minutes не указан
        """
        if expire_minutes is None and expire_days <= 0:
            raise ValueError("Срок действия ключа должен быть больше 0 дней")

        # v3: clients/add (или upsert через update, если клиент уже есть),
        # привязка к указанному inbound; uuid/password = единый секрет.
        if await self._ensure_api_version() == "v3":
            if expire_minutes is not None:
                expiry_ms = int((time.time() + expire_minutes * 60) * 1000)
            elif expire_days > 0:
                expiry_ms = int((time.time() + expire_days * 86400) * 1000)
            else:
                expiry_ms = 0
            total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
            import urllib.parse
            existing = await self._v3_get_client(email)
            if existing:
                secret = existing.get("uuid") or existing.get("password") or str(uuid.uuid4())
                sub_id = existing.get("subId") or uuid.uuid4().hex
                current_ids = set(existing.get("inboundIds") or [])
                ids = sorted(current_ids | {inbound_id})
                body = self._v3_client_body(
                    email=email, secret=secret, sub_id=sub_id, total_bytes=total_bytes,
                    expiry_ms=expiry_ms, limit_ip=limit_ip, enable=enable, tg_id=tg_id,
                    inbound_ids=ids, flow=flow,
                )
                enc = urllib.parse.quote(email, safe='')
                await self._v3_post_client(f"/panel/api/clients/update/{enc}", body)
                if inbound_id not in current_ids:
                    await self._v3_attach(email, [inbound_id])
            else:
                secret = str(uuid.uuid4())
                sub_id = uuid.uuid4().hex
                body = self._v3_client_body(
                    email=email, secret=secret, sub_id=sub_id, total_bytes=total_bytes,
                    expiry_ms=expiry_ms, limit_ip=limit_ip, enable=enable, tg_id=tg_id,
                    inbound_ids=[inbound_id], flow=flow,
                )
                await self._v3_post_client("/panel/api/clients/add", {"client": body, "inboundIds": [inbound_id]})
            return {
                "uuid": secret,
                "email": email,
                "inbound_id": inbound_id,
                "expire_time": expiry_ms,
                "total_gb": total_gb,
            }

        # Определяем протокол inbound для правильной структуры клиента
        protocol = ""
        method = ""
        existing_client_uuid = None  # UUID существующего клиента с таким email
        
        try:
            inbounds = await self.get_inbounds()
            for ib in inbounds:
                if ib['id'] == inbound_id:
                    protocol = ib.get('protocol', '')
                    settings_raw = ib.get('settings', '{}')
                    if isinstance(settings_raw, str):
                        settings = _as_obj(settings_raw)
                    else:
                        settings = settings_raw
                    method = settings.get('method', '')
                    
                    # Проверяем, не существует ли уже клиент с таким email
                    clients_list = (settings.get('clients') or [])
                    for existing_client in clients_list:
                        if existing_client.get('email') == email:
                            existing_client_uuid = existing_client.get('id') or existing_client.get('password')
                            logger.warning(f"⚠️ Клиент с email={email} уже существует на панели (UUID={existing_client_uuid})")
                            break
                    break
        except Exception:
            pass

        # Если клиент с таким email уже существует - удаляем его
        if existing_client_uuid:
            logger.info(f"🗑️ Удаляем существующего клиента {email} перед созданием нового...")
            try:
                await self.delete_client(inbound_id, existing_client_uuid)
                logger.info(f"✅ Существующий клиент {email} удалён")
            except Exception as e:
                logger.error(f"❌ Не удалось удалить существующего клиента {email}: {e}")

        client_uuid = str(uuid.uuid4())
        
        # Для Shadowsocks 2022 требуется base64 пароль определенной длины
        if protocol == 'shadowsocks':
            import base64
            import os
            if method.startswith('2022-'):
                if '128' in method:
                    client_uuid = base64.b64encode(os.urandom(16)).decode('utf-8')
                else:
                    client_uuid = base64.b64encode(os.urandom(32)).decode('utf-8')
            else:
                # Для обычного SS лучше тоже использовать base64 (надежнее, чем uuid с дефисами)
                client_uuid = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')

        # Время истечения (timestamp в мс)
        if expire_minutes is not None:
            # Используем минуты для тестовых ключей
            expire_time = int((time.time() + expire_minutes * 60) * 1000)
        elif expire_days > 0:
            expire_time = int((time.time() + expire_days * 86400) * 1000)
        else:
            expire_time = 0
        
        # Лимит трафика (байты)
        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
        
        # Базовая структура клиента (единый билдер для всех протоколов)
        client_entry = self._build_client_entry(
            protocol=protocol,
            secret=client_uuid,
            email=email,
            sub_id=uuid.uuid4().hex,
            total_bytes=total_bytes,
            expiry_ms=expire_time,
            limit_ip=limit_ip,
            enable=enable,
            tg_id=tg_id,
            flow=flow,
        )

        # Структура для 3X-UI
        client_data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [client_entry]
            })
        }
        
        response = await self._request("POST", "/panel/api/inbounds/addClient", data=client_data)
        
        # Проверяем успешность создания
        if not response.get("success", True):
            error_msg = response.get("msg", "Неизвестная ошибка")
            logger.error(f"Ошибка создания клиента на панели: {error_msg}")
            raise VPNAPIError(f"Ошибка создания клиента: {error_msg}")
        
        # Логируем для отладки
        logger.debug(f"Клиент создан на панели: email={email}, uuid={client_uuid}, response={response}")
        
        return {
            "uuid": client_uuid,
            "email": email,
            "inbound_id": inbound_id,
            "expire_time": expire_time,
            "total_gb": total_gb
        }
    
    async def get_inbound_flow(self, inbound_id: int) -> str:
        """
        Определяет нужное значение flow для inbound.
        Flow = 'xtls-rprx-vision' нужен только для VLESS + TCP + (Reality или TLS).
        """
        try:
            inbounds = await self.get_inbounds()
            for inbound in inbounds:
                if inbound['id'] == inbound_id:
                    protocol = inbound.get('protocol', '')
                    if protocol != 'vless':
                        return ""
                    
                    stream_raw = inbound.get('streamSettings', '{}')
                    if isinstance(stream_raw, str):
                        stream = _as_obj(stream_raw)
                    else:
                        stream = stream_raw
                    
                    network = stream.get('network', 'tcp')
                    security = stream.get('security', 'none')
                    
                    # Flow нужен только для VLESS + TCP + (reality | tls)
                    if network == 'tcp' and security in ('reality', 'tls'):
                        return 'xtls-rprx-vision'
                    return ""
        except Exception as e:
            logger.warning(f"Error determining flow for inbound {inbound_id}: {e}")
        return ""
    
    async def get_client_stats(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает статистику трафика и протокол конкретного клиента.
        
        Args:
            email: Email/идентификатор клиента
            
        Returns:
            Словарь со статистикой или None:
            - up: Трафик за всё время (up) байт
            - down: Трафик за всё время (down) байт
            - total: Лимит трафика (байт)
            - protocol: Протокол соединения (vless, vmess и т.д.)
        """
        try:
            inbounds = await self.get_inbounds()
            for inbound in inbounds:
                client_stats = inbound.get("clientStats", [])
                for stats in client_stats:
                    if stats.get("email") == email:
                        return {
                            "up": stats.get("up", 0),
                            "down": stats.get("down", 0),
                            "total": stats.get("total", 0),
                            "protocol": inbound.get("protocol", "vless"),
                            "remark": inbound.get("remark", ""),
                            "expiry_time": stats.get("expiryTime", 0)
                        }
        except Exception as e:
            logger.warning(f"Ошибка получения статистики клиента {email}: {e}")
        return None
    
    async def delete_client(self, inbound_id: int, client_uuid: str) -> bool:
        """
        Удаляет клиента из inbound.
        
        Args:
            inbound_id: ID inbound-подключения
            client_uuid: UUID клиента
            
        Returns:
            True при успешном удалении
        """
        import urllib.parse
        # v3: клиент удаляется целиком по email (из всех своих inbound).
        if await self._ensure_api_version() == "v3":
            email = await self._v3_email_for_secret(client_uuid)
            if not email:
                logger.info("delete_client v3: клиент с секретом не найден, считаем уже удалённым")
                return True
            enc = urllib.parse.quote(email, safe='')
            await self._request("POST", f"/panel/api/clients/del/{enc}")
            return True

        encoded_uuid = urllib.parse.quote(client_uuid, safe='')
        await self._request("POST", f"/panel/api/inbounds/{inbound_id}/delClient/{encoded_uuid}")
        return True


    async def update_client_traffic_limit(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        total_gb: int
    ) -> bool:
        """
        Обновляет лимит трафика существующего клиента.
        
        Args:
            inbound_id: ID inbound-подключения
            client_uuid: UUID клиента
            email: Email/идентификатор клиента
            total_gb: Новый лимит трафика в ГБ (0 = без лимита)
            
        Returns:
            True при успешном обновлении
        """
        # Получаем текущие данные клиента
        inbounds = await self.get_inbounds()
        target_inbound = None
        target_client = None
        
        for inbound in inbounds:
            if inbound.get('id') == inbound_id:
                target_inbound = inbound
                settings = _as_obj(inbound.get('settings', '{}'))
                clients = (settings.get('clients') or [])
                
                for client in clients:
                    if client.get('id') == client_uuid:
                        target_client = client
                        break
                break
        
        if not target_inbound or not target_client:
            raise VPNAPIError(f"Клиент {email} не найден в inbound {inbound_id}")
        
        # Обновляем лимит трафика
        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
        target_client['totalGB'] = total_bytes
        
        # Формируем данные для обновления
        settings = _as_obj(target_inbound.get('settings', '{}'))
        update_data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": target_client.get('id'),
                    "email": target_client.get('email'),
                    "limitIp": target_client.get('limitIp', 1),
                    "totalGB": total_bytes,
                    "expiryTime": target_client.get('expiryTime', 0),
                    "enable": target_client.get('enable', True),
                    "tgId": target_client.get('tgId', ''),
                    "subId": target_client.get('subId', ''),
                    "reset": target_client.get('reset', 0)
                }]
            })
        }
        
        import urllib.parse
        encoded_uuid = urllib.parse.quote(client_uuid, safe='')
        await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_uuid}", data=update_data)
        logger.info(f"Обновлен лимит трафика клиента {email}: {total_gb} ГБ")
        return True

    async def disable_reset_for_all_clients(self) -> int:
        """
        Отключает автопродление (сброс трафика/дней) при наступлении 1-го числа месяца для всех клиентов.
        Устанавливает поле reset = 0 для всех клиентов во всех inbounds.
        
        Returns:
            Количество обновленных клиентов.
        """
        updated_count = 0
        inbounds = await self.get_inbounds()
        
        for inbound in inbounds:
            settings_raw = inbound.get('settings', '{}')
            settings = json.loads(settings_raw) if isinstance(settings_raw, str) else settings_raw
            clients = (settings.get('clients') or [])
            
            for client in clients:
                if client.get('reset', 0) != 0:  # только если reset не 0
                    
                    # clientId — это id(uuid) для vless/vmess, password для trojan/shadowsocks
                    client_id = client.get('id') or client.get('password')
                    
                    if client_id:
                        # Формируем правильную структуру клиента для обновления, сохраняя нужные поля
                        updated_client = {
                            "id": client.get('id', ''),
                            "password": client.get('password', ''),
                            "flow": client.get('flow', ''),
                            "email": client.get('email', ''),
                            "limitIp": client.get('limitIp', 1),
                            "totalGB": client.get('totalGB', 0),
                            "expiryTime": client.get('expiryTime', 0),
                            "enable": client.get('enable', True),
                            "tgId": client.get('tgId', ''),
                            "subId": client.get('subId', ''),
                            "reset": 0  # Сбрасываем reset
                        }
                        
                        # Удаляем пустые поля (важно для разных протоколов)
                        updated_client = {k: v for k, v in updated_client.items() if v != ''}
                        
                        client_data = {
                            "id": inbound['id'],
                            "settings": json.dumps({"clients": [updated_client]})
                        }
                        
                        try:
                            # В 3x-ui мы отправляем POST /panel/api/inbounds/updateClient/:clientId
                            # А в теле запроса передаем id инбаунда и новый объект clients
                            import urllib.parse
                            # Кодируем ID/пароль для URL, чтобы слеши в base64 (Shadowsocks) не ломали HTTP-маршрутизацию
                            encoded_id = urllib.parse.quote(client_id, safe='')
                            await self._request(
                                "POST",
                                f"/panel/api/inbounds/updateClient/{encoded_id}",
                                data=client_data
                            )
                            updated_count += 1
                            logger.info(f"Отключено автопродление (reset=0) для клиента {client.get('email', client_id)}")
                        except Exception as e:
                            logger.error(f"Ошибка при отключении автопродления для клиента {client.get('email', client_id)}: {e}")
                            
        return updated_count

    async def update_client_full(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        expiry_time_ms: int,
        total_gb_bytes: int,
        enable: bool = True
    ) -> bool:
        """
        Обновляет ВСЕ параметры клиента на панели данными из нашей БД.
        Единственная функция записи на панель (кроме создания/удаления).
        
        Протокольные поля (flow, subId, limitIp, tgId) читаются с панели,
        но expiryTime и totalGB ВСЕГДА берутся из параметров (из нашей БД).
        
        Args:
            inbound_id: ID inbound-подключения (хинт; обновляем во ВСЕХ inbound,
                где живёт клиент)
            client_uuid: UUID/секрет клиента
            email: Email/идентификатор клиента
            expiry_time_ms: Срок действия в миллисекундах (из нашей БД, 0 = бессрочный)
            total_gb_bytes: Лимит трафика в байтах (из нашей БД, 0 = безлимит)
            enable: Включён ли ключ (True = включён, False = отключён)

        Returns:
            True при успешном обновлении хотя бы в одном inbound
        """
        import urllib.parse

        # v3: один клиент с inboundIds — обновляем одним вызовом по email.
        if await self._ensure_api_version() == "v3":
            await self._v3_update_fields(
                email, expiryTime=expiry_time_ms, totalGB=total_gb_bytes, enable=enable
            )
            from datetime import datetime
            expiry_str = datetime.fromtimestamp(expiry_time_ms / 1000).strftime('%Y-%m-%d %H:%M') if expiry_time_ms > 0 else '∞'
            logger.info(f"[v3] Обновлён клиент {email}: expiry={expiry_str}, enable={enable}")
            return True

        # Клиент зеркалируется во все inbound сервера под одним секретом/email,
        # поэтому обновляем его в КАЖДОМ inbound, где он найден.
        inbounds = await self.get_inbounds()
        updated_any = False

        for inbound in inbounds:
            ib_id = inbound.get('id')
            settings = _as_obj(inbound.get('settings', '{}'))
            target_client = None
            for client in (settings.get('clients') or []):
                if (client.get('id') == client_uuid
                        or client.get('password') == client_uuid
                        or client.get('email') == email):
                    target_client = client
                    break
            if not target_client:
                continue

            # expiryTime и totalGB из ПАРАМЕТРОВ (нашей БД), остальное — с панели
            updated_client = {
                "id": target_client.get('id', ''),
                "password": target_client.get('password', ''),
                "flow": target_client.get('flow', ''),
                "email": target_client.get('email', email),
                "limitIp": target_client.get('limitIp', 1),
                "totalGB": total_gb_bytes,
                "expiryTime": expiry_time_ms,
                "enable": enable,
                "tgId": target_client.get('tgId', ''),
                "subId": target_client.get('subId', ''),
                "reset": 0,
            }
            updated_client = {k: v for k, v in updated_client.items() if v != ''}

            update_data = {"id": ib_id, "settings": json.dumps({"clients": [updated_client]})}
            client_id = target_client.get('id') or target_client.get('password') or client_uuid
            encoded_id = urllib.parse.quote(client_id, safe='')
            try:
                await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_id}", data=update_data)
                updated_any = True
            except Exception as e:
                logger.error(f"Ошибка обновления клиента {email} в inbound {ib_id}: {e}")

        if not updated_any:
            raise VPNAPIError(f"Клиент {email} не найден ни в одном inbound")

        from datetime import datetime
        expiry_str = datetime.fromtimestamp(expiry_time_ms / 1000).strftime('%Y-%m-%d %H:%M') if expiry_time_ms > 0 else '∞'
        limit_str = f"{total_gb_bytes / 1024**3:.1f} ГБ" if total_gb_bytes > 0 else '∞'
        logger.info(f"Обновлён клиент {email} во всех inbound: expiry={expiry_str}, limit={limit_str}")
        return True

    async def extend_client_expiry(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        days: int
    ) -> bool:
        """
        Продлевает срок действия клиента на указанное количество дней.
        Если срок уже истек, прибавляет дни к текущему времени.
        
        Args:
            inbound_id: ID inbound-подключения
            client_uuid: UUID клиента
            email: Email/идентификатор клиента
            days: Количество дней для продления
            
        Returns:
            True при успешном обновлении
        """
        import time
        import urllib.parse

        # v3: читаем текущий срок клиента и продлеваем одним вызовом по email.
        if await self._ensure_api_version() == "v3":
            cur = await self._v3_get_client(email)
            if not cur:
                raise VPNAPIError(f"Клиент {email} не найден на панели (v3)")
            current_expiry = cur.get("expiryTime", 0) or 0
            now_ms = int(time.time() * 1000)
            ext_ms = days * 86400 * 1000
            if current_expiry == 0:
                new_expiry = 0  # бессрочный остаётся бессрочным
            elif current_expiry < now_ms:
                new_expiry = now_ms + ext_ms
            else:
                new_expiry = current_expiry + ext_ms
            await self._v3_update_fields(email, expiryTime=new_expiry)
            logger.info(f"[v3] Продлён ключ клиента {email} на {days} дней. Новый expiry: {new_expiry}")
            return True

        # Продлеваем во ВСЕХ inbound, где живёт клиент.
        inbounds = await self.get_inbounds()
        current_time_ms = int(time.time() * 1000)
        extension_ms = days * 86400 * 1000
        updated_any = False
        last_expiry = 0

        for inbound in inbounds:
            ib_id = inbound.get('id')
            settings = _as_obj(inbound.get('settings', '{}'))
            target_client = None
            for client in (settings.get('clients') or []):
                if (client.get('id') == client_uuid
                        or client.get('password') == client_uuid
                        or client.get('email') == email):
                    target_client = client
                    break
            if not target_client:
                continue

            current_expiry = target_client.get('expiryTime', 0)
            if current_expiry == 0:
                new_expiry = 0  # бессрочный остаётся бессрочным
            elif current_expiry < current_time_ms:
                new_expiry = current_time_ms + extension_ms
            else:
                new_expiry = current_expiry + extension_ms
            last_expiry = new_expiry

            updated_client = {
                "id": target_client.get('id', ''),
                "password": target_client.get('password', ''),
                "flow": target_client.get('flow', ''),
                "email": target_client.get('email', ''),
                "limitIp": target_client.get('limitIp', 1),
                "totalGB": target_client.get('totalGB', 0),
                "expiryTime": new_expiry,
                "enable": target_client.get('enable', True),
                "tgId": target_client.get('tgId', ''),
                "subId": target_client.get('subId', ''),
                "reset": target_client.get('reset', 0),
            }
            updated_client = {k: v for k, v in updated_client.items() if v != ''}
            update_data = {"id": ib_id, "settings": json.dumps({"clients": [updated_client]})}

            client_id = target_client.get('id') or target_client.get('password') or client_uuid
            encoded_id = urllib.parse.quote(client_id, safe='')
            try:
                await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_id}", data=update_data)
                updated_any = True
            except Exception as e:
                logger.error(f"Ошибка продления {email} в inbound {ib_id}: {e}")

        if not updated_any:
            raise VPNAPIError(f"Клиент {email} не найден ни в одном inbound")

        logger.info(f"Продлен ключ клиента {email} на {days} дней. Новый expiry: {last_expiry}")
        return True

    def _build_client_config(
        self,
        inbound: Dict[str, Any],
        settings: Dict[str, Any],
        target_client: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Собирает клиентский конфиг из inbound и записи клиента."""
        stream_raw = inbound.get("streamSettings", "{}")
        stream_settings = json.loads(stream_raw) if isinstance(stream_raw, str) else stream_raw
        protocol = inbound.get("protocol", "vless")
        email = target_client.get("email", "")

        logger.debug(f"Stream settings for {email}: {json.dumps(stream_settings, ensure_ascii=False)}")
        if stream_settings.get("security") == "reality":
            reality = stream_settings.get("realitySettings", {})
            logger.debug(
                "Reality settings for %s: pbk=%s, sni=%s, fp=%s, shortIds=%s",
                email,
                reality.get("publicKey"),
                reality.get("serverName"),
                reality.get("fingerprint"),
                reality.get("shortIds"),
            )

        result: Dict[str, Any] = {
            "uuid": target_client.get("id", ""),
            "email": email,
            "port": inbound["port"],
            "protocol": protocol,
            "host": self.server["host"],
            "stream_settings": stream_settings,
            "inbound_name": inbound.get("remark", "VPN"),
            "server_name": self.server.get("name", "VPN Server"),
            "sub_id": target_client.get("subId", ""),
            "flow": target_client.get("flow", "")
        }

        if protocol == 'trojan':
            result["password"] = target_client.get("password", target_client.get("id", ""))
        elif protocol == 'shadowsocks':
            result["method"] = settings.get("method", "aes-256-gcm")
            result["password"] = target_client.get("password", settings.get("password", ""))
            result["server_password"] = settings.get("password", "")
        elif protocol == 'vmess':
            result["security_method"] = target_client.get("security", "auto")
        elif protocol in ('hysteria2', 'hysteria'):
            # Hysteria2: аутентификация по password; TLS/obfs — параметры inbound
            result["protocol"] = "hysteria2"
            result["password"] = target_client.get("password", target_client.get("id", ""))
            tls = stream_settings.get("tlsSettings", {}) or {}
            result["sni"] = tls.get("serverName", "") or self.server["host"]
            result["insecure"] = 1 if tls.get("allowInsecure") else 0
            obfs = settings.get("obfs")
            if isinstance(obfs, dict) and obfs.get("type"):
                result["obfs"] = obfs.get("type")
                result["obfs_password"] = obfs.get("password", "")

        return result

    async def get_client_configs(self, emails: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Получает конфигурации сразу для нескольких клиентов одним чтением inbounds.
        
        Args:
            emails: Список email/идентификаторов клиентов
            
        Returns:
            Словарь вида {email: config}
        """
        email_set = {email for email in emails if email}
        if not email_set:
            return {}

        configs: Dict[str, Dict[str, Any]] = {}

        # v3: клиенты централизованы (clients/list + inboundIds), settings.clients
        # у inbound может быть пуст — читаем по v3-пути.
        if await self._ensure_api_version() == "v3":
            try:
                by_email = await self._v3_configs_by_inbound(email_set, multi=False)
                return {e: cfgs[0] for e, cfgs in by_email.items() if cfgs}
            except Exception as e:
                logger.error(f"[v3] Error getting client configs: {e}")
                return {}

        try:
            # VLESS-inbound идут первыми, чтобы одиночный конфиг (key_sender/QR)
            # отдавал основную VLESS-ссылку.
            inbounds = self._sort_inbounds_vless_first(await self.get_inbounds())
            for inbound in inbounds:
                if inbound.get("protocol") not in self.SUPPORTED_PROTOCOLS:
                    continue
                settings = _as_obj(inbound.get("settings", "{}"))
                clients = (settings.get("clients") or [])

                for client in clients:
                    email = client.get("email", "")
                    if email not in email_set or email in configs:
                        continue
                    configs[email] = self._build_client_config(inbound, settings, client)

                if len(configs) == len(email_set):
                    break
        except Exception as e:
            logger.error(f"Error getting client configs: {e}")

        return configs

    @staticmethod
    def _sort_inbounds_vless_first(inbounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Сортирует inbound так, чтобы VLESS шли первыми (стабильный порядок)."""
        return sorted(inbounds, key=lambda ib: (ib.get("protocol") != "vless", ib.get("id", 0)))

    async def get_all_client_configs(self, emails: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Возвращает конфиги для КАЖДОГО inbound, где найден клиент (по email).

        В отличие от get_client_configs (один конфиг на email), используется
        подпиской: одна подписка отдаёт по ссылке на каждый inbound сервера.

        Returns:
            {email: [config, ...]} — порядок: VLESS первым, затем остальные.
        """
        email_set = {email for email in emails if email}
        if not email_set:
            return {}

        configs: Dict[str, List[Dict[str, Any]]] = {email: [] for email in email_set}

        # v3: один конфиг на каждый привязанный inbound через clients/list+inboundIds.
        if await self._ensure_api_version() == "v3":
            try:
                return await self._v3_configs_by_inbound(email_set, multi=True)
            except Exception as e:
                logger.error(f"[v3] Error getting all client configs: {e}")
                return {}

        try:
            inbounds = await self.get_inbounds()
            for inbound in inbounds:
                if inbound.get("protocol") not in self.SUPPORTED_PROTOCOLS:
                    continue
                settings = _as_obj(inbound.get("settings", "{}"))
                for client in (settings.get("clients") or []):
                    email = client.get("email", "")
                    if email not in email_set:
                        continue
                    configs[email].append(self._build_client_config(inbound, settings, client))
        except Exception as e:
            logger.error(f"Error getting all client configs: {e}")

        # Убираем email без единого конфига
        return {email: cfgs for email, cfgs in configs.items() if cfgs}

    async def get_client_config(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает полную конфигурацию клиента для подключения (первичный inbound).

        Args:
            email: Email/идентификатор клиента

        Returns:
            Словарь с настройками подключения или None
        """
        configs = await self.get_client_configs([email])
        return configs.get(email)

    async def get_subscription_link(self, sub_id: str) -> Optional[str]:
        """
        Получает VLESS-ссылку через endpoint подписки.
        
        Args:
            sub_id: Subscription ID клиента
            
        Returns:
            Готовая VLESS-ссылка или None если не удалось получить
        """
        session = await self._ensure_session()
        
        # Строим список URL кандидатов
        # 1. С base_path
        # 2. Без base_path
        # 3. /subscribe/ вместо /sub/ (иногда бывает)
        
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        host_url = f"{parsed.scheme}://{parsed.netloc}"
        
        candidates = [
            f"{self.base_url}/sub/{sub_id}",
            f"{host_url}/sub/{sub_id}",
            f"{self.base_url}/subscribe/{sub_id}",
            f"{host_url}/subscribe/{sub_id}"
        ]
        
        for url in candidates:
            try:
                # Важно: Не используем _request, так как это публичный endpoint
                async with session.get(url, ssl=False) as response:
                    logger.info(f"Sub URL probe: {url} -> {response.status}")
                    
                    if response.status == 200:
                        text = await response.text()
                        text = text.strip()
                        
                        # Если вернул VLESS
                        if text.startswith("vless://") or text.startswith("vmess://") or text.startswith("trojan://"):
                            return text
                        
                        # Если вернул base64
                        try:
                            import base64
                            # Добавляем паддинг если нужно
                            missing_padding = len(text) % 4
                            if missing_padding:
                                text += '=' * (4 - missing_padding)
                            decoded = base64.b64decode(text).decode('utf-8').strip()
                            if decoded.startswith("vless://") or decoded.startswith("vmess://") or decoded.startswith("trojan://"):
                                return decoded
                        except:
                            # Логируем, если это что-то странное
                            if len(text) < 200:
                                logger.debug(f"Unknown response text: {text}")
                            pass
            except Exception as e:
                logger.warning(f"Ошибка получения подписки ({url}): {e}")
            
        return None

    async def get_database_backup(self) -> bytes:
        """
        Скачивает резервную копию базы данных панели.
        
        Endpoint: GET /panel/api/server/getDb (или фолбэки)
        
        Returns:
            Бинарные данные файла x-ui.db
            
        Raises:
            VPNAPIError: При ошибке скачивания
        """
        session = await self._ensure_session()
        
        # Авторизуемся если нужно
        if not self.is_authenticated:
            await self.login()
        
        headers = {
            "Accept": "application/octet-stream",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Разные версии X-UI / 3X-UI используют разные пути для скачивания БД
        endpoints = [
            "/panel/api/server/getDb",
            "/panel/setting/getDb",
            "/panel/api/getDb",
            "/server/getDb"
        ]
        
        last_status = None
        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                async with session.get(url, headers=headers) as response:
                    last_status = response.status
                    if response.status == 200:
                        data = await response.read()
                        
                        # Проверяем, что скачался действительно SQLite файл
                        # SQLite файлы всегда начинаются с байтов 'SQLite format 3\000'
                        if data.startswith(b'SQLite format 3\x00'):
                            logger.info(f"Скачан бэкап БД панели ({endpoint}): {len(data)} байт")
                            return data
                        else:
                            text = data[:100].decode(errors='ignore')
                            logger.debug(f"Endpoint {endpoint} вернул не БД, а: {text}...")
            except aiohttp.ClientError as e:
                logger.debug(f"Ошибка HTTP при проверке {endpoint}: {e}")
                
        raise VPNAPIError(f"Ошибка скачивания бэкапа: ни один endpoint не вернул файл БД. Последний HTTP статус: {last_status}")

    async def reset_client_traffic(self, inbound_id: int, email: str) -> bool:
        """
        Сбрасывает счётчики трафика (up/down) клиента на панели.
        
        Endpoint: POST /panel/api/inbounds/{inbound_id}/resetClientTraffic/{email}

        Сбрасываем счётчики во ВСЕХ inbound, где есть клиент с этим email.

        Args:
            inbound_id: ID inbound-подключения (хинт; не ограничивает)
            email: Email/идентификатор клиента

        Returns:
            True если сброшено хотя бы в одном inbound
        """
        import urllib.parse
        encoded_email = urllib.parse.quote(email, safe='')

        # v3: сброс трафика клиента одним вызовом по email.
        if await self._ensure_api_version() == "v3":
            try:
                await self._request("POST", f"/panel/api/clients/resetTraffic/{encoded_email}")
                logger.info(f"[v3] Сброшен трафик клиента {email}")
                return True
            except Exception as e:
                logger.error(f"[v3] Ошибка сброса трафика {email}: {e}")
                return False

        inbounds = await self.get_inbounds()
        done = 0
        for inbound in inbounds:
            settings = _as_obj(inbound.get('settings', '{}'))
            if not any(c.get('email') == email for c in (settings.get('clients') or [])):
                continue
            ib_id = inbound.get('id')
            try:
                await self._request(
                    "POST",
                    f"/panel/api/inbounds/{ib_id}/resetClientTraffic/{encoded_email}"
                )
                done += 1
            except Exception as e:
                logger.error(f"Ошибка сброса трафика {email} в inbound {ib_id}: {e}")

        logger.info(f"Сброшен трафик клиента {email} в {done} inbound(ах)")
        return done > 0

    async def update_client_limit(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        total_gb_bytes: int
    ) -> bool:
        """
        Обновляет лимит трафика (totalGB) клиента во ВСЕХ inbound, где он есть.

        Args:
            inbound_id: ID inbound-подключения (хинт; не ограничивает)
            client_uuid: UUID/секрет клиента
            email: Email/идентификатор клиента
            total_gb_bytes: Новый лимит в байтах

        Returns:
            True если обновлено хотя бы в одном inbound
        """
        import urllib.parse

        # v3: обновляем лимит одним вызовом по email.
        if await self._ensure_api_version() == "v3":
            await self._v3_update_fields(email, totalGB=total_gb_bytes)
            logger.info(f"[v3] Обновлён лимит клиента {email}: {total_gb_bytes / (1024**3):.1f} ГБ")
            return True

        inbounds = await self.get_inbounds()
        updated_any = False

        for inbound in inbounds:
            ib_id = inbound.get('id')
            settings = _as_obj(inbound.get('settings', '{}'))
            target_client = None
            for client in (settings.get('clients') or []):
                if (client.get('id') == client_uuid
                        or client.get('password') == client_uuid
                        or client.get('email') == email):
                    target_client = client
                    break
            if not target_client:
                continue

            updated_client = {
                "id": target_client.get('id', ''),
                "password": target_client.get('password', ''),
                "flow": target_client.get('flow', ''),
                "email": target_client.get('email', ''),
                "limitIp": target_client.get('limitIp', 1),
                "totalGB": total_gb_bytes,
                "expiryTime": target_client.get('expiryTime', 0),
                "enable": target_client.get('enable', True),
                "tgId": target_client.get('tgId', ''),
                "subId": target_client.get('subId', ''),
                "reset": target_client.get('reset', 0),
            }
            updated_client = {k: v for k, v in updated_client.items() if v != ''}
            update_data = {"id": ib_id, "settings": json.dumps({"clients": [updated_client]})}

            client_id = target_client.get('id') or target_client.get('password') or client_uuid
            encoded_id = urllib.parse.quote(client_id, safe='')
            try:
                await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_id}", data=update_data)
                updated_any = True
            except Exception as e:
                logger.error(f"Ошибка обновления лимита {email} в inbound {ib_id}: {e}")

        if not updated_any:
            raise VPNAPIError(f"Клиент {email} не найден ни в одном inbound")

        limit_gb = total_gb_bytes / (1024**3)
        logger.info(f"Обновлён лимит клиента {email} во всех inbound: {limit_gb:.1f} ГБ")
        return True

    async def close(self):
        """Закрывает сессию."""
        if self.session:
            await self.session.close()
            self.session = None


# ============================================================================
# Глобальный кэш клиентов и вспомогательные функции
# ============================================================================
