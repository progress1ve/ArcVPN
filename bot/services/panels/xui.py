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
import uuid
import time
from typing import Optional, Dict, Any, List
from config import RETRY_CONFIG

logger = logging.getLogger(__name__)


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
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_authenticated = False
        
        logger.debug(f"Инициализирован XUIClient для {server['name']}: {self.base_url}")
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Создаёт сессию если её нет."""
        if self.session is None or self.session.closed:
            # Unsafe=True важно для IP-адресов и самоподписанных сертификатов
            connector = aiohttp.TCPConnector(ssl=False)
            jar = aiohttp.CookieJar(unsafe=True)
            timeout = aiohttp.ClientTimeout(total=5)
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
        logger.debug(f"Сессия сброшена для {self.server['name']}")
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        retry: bool = True,
        log_error: bool = True
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
        
        # Стандартные заголовки для AJAX запросов 3X-UI
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
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
                
                logger.debug(f"API запрос: {method} {url}")
                
                async with session.request(method, url, json=data, headers=headers) as response:
                    text = await response.text()
                    
                    # Обработка статусов
                    if response.status == 200:
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

    async def login(self) -> bool:
        """
        Авторизация в панели 3X-UI.
        
        Returns:
            True при успешной авторизации
            
        Raises:
            VPNAPIError: При ошибке авторизации
        """
        logger.info(f"Авторизация на {self.server['name']}...")
        
        session = await self._ensure_session()
        url = f"{self.base_url}/login"
        
        try:
            async with session.post(url, json={
                "username": self.server["login"],
                "password": self.server["password"]
            }) as resp:
                text = await resp.text()
                if resp.status == 200:
                    data = json.loads(text)
                    if data.get("success"):
                        self.is_authenticated = True
                        logger.info("✅ Успешная авторизация")
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
                    settings = json.loads(settings_str)
                    clients = settings.get("clients", [])
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
            # Запрос к /panel/api/inbounds/onlines
            response = await self._request("POST", "/panel/api/inbounds/onlines", retry=False, log_error=False)
            if response.get("success") and response.get("obj"):
                return len(response["obj"])
        except VPNAPIError:
            pass
        except Exception as e:
            logger.debug(f"Ошибка получения online пользователей: {e}")
        return 0

    async def add_client(
        self,
        inbound_id: int,
        email: str,
        total_gb: int = 0,
        expire_days: int = 30,
        limit_ip: int = 1,
        enable: bool = True,
        tg_id: str = "",
        flow: str = ""
    ) -> Dict[str, Any]:
        """
        Добавляет клиента в inbound.
        
        Args:
            inbound_id: ID inbound-подключения
            email: Уникальный идентификатор клиента (используем user_{id})
            total_gb: Лимит трафика в ГБ (0 = без лимита)
            expire_days: Срок действия в днях (0 = бессрочно)
            limit_ip: Ограничение по IP (1 = 1 устройство)
            enable: Активен ли клиент
            tg_id: Telegram ID для уведомлений панели
            flow: Параметр flow (напр. 'xtls-rprx-vision' для VLESS Reality/TLS TCP)
            
        Returns:
            Словарь с данными созданного клиента
            
        Raises:
            ValueError: Если expire_days <= 0
        """
        if expire_days <= 0:
            raise ValueError("Срок действия ключа должен быть больше 0 дней")

        # Определяем протокол inbound для правильной структуры клиента
        protocol = ""
        method = ""
        try:
            inbounds = await self.get_inbounds()
            for ib in inbounds:
                if ib['id'] == inbound_id:
                    protocol = ib.get('protocol', '')
                    settings_raw = ib.get('settings', '{}')
                    if isinstance(settings_raw, str):
                        settings = json.loads(settings_raw)
                    else:
                        settings = settings_raw
                    method = settings.get('method', '')
                    break
        except Exception:
            pass

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
        expire_time = int((time.time() + expire_days * 86400) * 1000) if expire_days > 0 else 0
        
        # Лимит трафика (байты)
        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
        
        # Базовая структура клиента
        client_entry = {
            "email": email,
            "limitIp": limit_ip,
            "totalGB": total_bytes,
            "expiryTime": expire_time,
            "enable": enable,
            "tgId": tg_id,
            "subId": uuid.uuid4().hex,
            "reset": 0,
        }
        
        # Протокол-зависимые поля
        if protocol == 'trojan':
            # Trojan использует password вместо id
            client_entry["password"] = client_uuid
            client_entry["flow"] = flow
        elif protocol == 'shadowsocks':
            # Shadowsocks — клиенты наследуют password/method из inbound
            client_entry["password"] = client_uuid
            client_entry["method"] = ""
        else:
            # VLESS / VMess — используют id (UUID)
            client_entry["id"] = client_uuid
            client_entry["flow"] = flow
        
        # Структура для 3X-UI
        client_data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [client_entry]
            })
        }
        
        await self._request("POST", "/panel/api/inbounds/addClient", data=client_data)
        
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
                        stream = json.loads(stream_raw)
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
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                
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
        settings = json.loads(target_inbound.get('settings', '{}'))
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
            clients = settings.get('clients', [])
            
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
        total_gb_bytes: int
    ) -> bool:
        """
        Обновляет ВСЕ параметры клиента на панели данными из нашей БД.
        Единственная функция записи на панель (кроме создания/удаления).
        
        Протокольные поля (flow, subId, limitIp, tgId) читаются с панели,
        но expiryTime и totalGB ВСЕГДА берутся из параметров (из нашей БД).
        
        Args:
            inbound_id: ID inbound-подключения
            client_uuid: UUID клиента
            email: Email/идентификатор клиента
            expiry_time_ms: Срок действия в миллисекундах (из нашей БД, 0 = бессрочный)
            total_gb_bytes: Лимит трафика в байтах (из нашей БД, 0 = безлимит)
            
        Returns:
            True при успешном обновлении
        """
        # Читаем текущие данные клиента с панели — только для протокольных полей
        inbounds = await self.get_inbounds()
        target_client = None
        
        for inbound in inbounds:
            if inbound.get('id') == inbound_id:
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                
                for client in clients:
                    if client.get('id') == client_uuid or client.get('password') == client_uuid:
                        target_client = client
                        break
                break
        
        if not target_client:
            raise VPNAPIError(f"Клиент {email} не найден в inbound {inbound_id}")
        
        # Формируем данные: expiryTime и totalGB из ПАРАМЕТРОВ (нашей БД),
        # остальное — из текущих данных клиента на панели
        updated_client = {
            "id": target_client.get('id', ''),
            "password": target_client.get('password', ''),
            "flow": target_client.get('flow', ''),
            "email": target_client.get('email', email),
            "limitIp": target_client.get('limitIp', 1),
            "totalGB": total_gb_bytes,          # ← Из нашей БД!
            "expiryTime": expiry_time_ms,        # ← Из нашей БД!
            "enable": target_client.get('enable', True),
            "tgId": target_client.get('tgId', ''),
            "subId": target_client.get('subId', ''),
            "reset": 0  # Не используем auto-reset панели
        }
        
        # Удаляем пустые строковые поля (для разных протоколов)
        updated_client = {k: v for k, v in updated_client.items() if v != ''}
        
        update_data = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [updated_client]})
        }
        
        import urllib.parse
        encoded_uuid = urllib.parse.quote(client_uuid, safe='')
        await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_uuid}", data=update_data)
        
        from datetime import datetime
        expiry_str = datetime.fromtimestamp(expiry_time_ms / 1000).strftime('%Y-%m-%d %H:%M') if expiry_time_ms > 0 else '∞'
        limit_str = f"{total_gb_bytes / 1024**3:.1f} ГБ" if total_gb_bytes > 0 else '∞'
        logger.info(f"Обновлён клиент {email}: expiry={expiry_str}, limit={limit_str}")
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
        
        # Получаем текущие данные клиента
        inbounds = await self.get_inbounds()
        target_inbound = None
        target_client = None
        
        for inbound in inbounds:
            if inbound.get('id') == inbound_id:
                target_inbound = inbound
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                
                for client in clients:
                    if client.get('id') == client_uuid or client.get('password') == client_uuid:
                        target_client = client
                        break
                break
                
        if not target_inbound or not target_client:
            raise VPNAPIError(f"Клиент {email} не найден в inbound {inbound_id}")
            
        current_time_ms = int(time.time() * 1000)
        current_expiry = target_client.get('expiryTime', 0)
        
        # Расчет нового времени истечения
        extension_ms = days * 86400 * 1000
        if current_expiry == 0:
            # Бесконечный ключ остается бесконечным
            new_expiry = 0
        elif current_expiry < current_time_ms:
            # Если ключ уже истек, прибавляем к текущему моменту
            new_expiry = current_time_ms + extension_ms
        else:
            # Если еще активен, прибавляем к текущему сроку окончания
            new_expiry = current_expiry + extension_ms
            
        target_client['expiryTime'] = new_expiry
        
        # Формируем данные для обновления
        update_data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
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
                    "reset": target_client.get('reset', 0)
                }]
            })
        }
        
        # Удаляем пустые поля (важно для разных протоколов, где id или password могут отсутствовать)
        clients_array = json.loads(update_data["settings"])["clients"][0]
        clients_array = {k: v for k, v in clients_array.items() if v != ''}
        update_data["settings"] = json.dumps({"clients": [clients_array]})
        
        import urllib.parse
        encoded_uuid = urllib.parse.quote(client_uuid, safe='')
        await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_uuid}", data=update_data)
        logger.info(f"Продлен ключ клиента {email} на {days} дней. Новый expiry: {new_expiry}")
        return True

    async def get_client_config(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает полную конфигурацию клиента для подключения.
        
        Args:
            email: Email/идентификатор клиента
            
        Returns:
            Словарь с настройками подключения или None
        """
        try:
            inbounds = await self.get_inbounds()
            for inbound in inbounds:
                settings = json.loads(inbound.get("settings", "{}"))
                clients = settings.get("clients", [])
                
                target_client = None
                for client in clients:
                    if client.get("email") == email:
                        target_client = client
                        break
                
                if target_client:
                    # Нашли клиента, возвращаем конфигурацию
                    stream_settings = json.loads(inbound.get("streamSettings", "{}"))
                    protocol = inbound.get("protocol", "vless")
                    
                    # DEBUG: логируем stream_settings для отладки Reality-параметров
                    logger.debug(f"Stream settings for {email}: {json.dumps(stream_settings, ensure_ascii=False)}")
                    if stream_settings.get("security") == "reality":
                        reality = stream_settings.get("realitySettings", {})
                        logger.info(f"Reality settings for {email}: pbk={reality.get('publicKey')}, sni={reality.get('serverName')}, fp={reality.get('fingerprint')}, shortIds={reality.get('shortIds')}")
                    
                    result = {
                        "uuid": target_client.get("id", ""),
                        "email": target_client.get("email", ""),
                        "port": inbound["port"],
                        "protocol": protocol,
                        "host": self.server["host"],
                        "stream_settings": stream_settings,
                        "inbound_name": inbound.get("remark", "VPN"),
                        "sub_id": target_client.get("subId", ""),
                        "flow": target_client.get("flow", "")
                    }
                    
                    # Протокол-специфичные поля
                    if protocol == 'trojan':
                        result["password"] = target_client.get("password", target_client.get("id", ""))
                    elif protocol == 'shadowsocks':
                        # Для Shadowsocks method хранится в inbound settings, 
                        # а пароль у каждого клиента свой (с fallback на общие)
                        result["method"] = settings.get("method", "aes-256-gcm")
                        result["password"] = target_client.get("password", settings.get("password", ""))
                        result["server_password"] = settings.get("password", "")
                    elif protocol == 'vmess':
                        result["security_method"] = target_client.get("security", "auto")
                    
                    return result
        except Exception as e:
            logger.error(f"Error getting client config for {email}: {e}")
        return None

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
        
        Args:
            inbound_id: ID inbound-подключения
            email: Email/идентификатор клиента
            
        Returns:
            True при успешном сбросе
        """
        import urllib.parse
        encoded_email = urllib.parse.quote(email, safe='')
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/resetClientTraffic/{encoded_email}"
        )
        logger.info(f"Сброшен трафик клиента {email} (inbound {inbound_id})")
        return True

    async def update_client_limit(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        total_gb_bytes: int
    ) -> bool:
        """
        Обновляет лимит трафика (totalGB) клиента на панели.
        
        Args:
            inbound_id: ID inbound-подключения
            client_uuid: UUID клиента
            email: Email/идентификатор клиента
            total_gb_bytes: Новый лимит в байтах
            
        Returns:
            True при успешном обновлении
        """
        # Получаем текущие данные клиента
        inbounds = await self.get_inbounds()
        target_client = None
        
        for inbound in inbounds:
            if inbound.get('id') == inbound_id:
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                
                for client in clients:
                    if client.get('id') == client_uuid or client.get('password') == client_uuid:
                        target_client = client
                        break
                break
        
        if not target_client:
            raise VPNAPIError(f"Клиент {email} не найден в inbound {inbound_id}")
        
        # Обновляем totalGB
        target_client['totalGB'] = total_gb_bytes
        
        # Формируем данные для обновления
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
            "reset": target_client.get('reset', 0)
        }
        
        # Удаляем пустые строковые поля (важно для разных протоколов)
        updated_client = {k: v for k, v in updated_client.items() if v != ''}
        
        update_data = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [updated_client]})
        }
        
        import urllib.parse
        encoded_uuid = urllib.parse.quote(client_uuid, safe='')
        await self._request("POST", f"/panel/api/inbounds/updateClient/{encoded_uuid}", data=update_data)
        
        limit_gb = total_gb_bytes / (1024**3)
        logger.info(f"Обновлён лимит клиента {email}: {limit_gb:.1f} ГБ")
        return True

    async def close(self):
        """Закрывает сессию."""
        if self.session:
            await self.session.close()
            self.session = None


# ============================================================================
# Глобальный кэш клиентов и вспомогательные функции
# ============================================================================
