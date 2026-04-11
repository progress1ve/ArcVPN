"""
Утилиты для работы с Git.

Функции для проверки обновлений, выполнения git pull и перезапуска бота.
"""
import subprocess
import logging
import sys
import os
from typing import Tuple, Optional, List, Dict

logger = logging.getLogger(__name__)


def get_project_root() -> str:
    """
    Получает корневую директорию проекта.
    
    Returns:
        Абсолютный путь к корню проекта
    """
    # Поднимаемся от bot/utils/ к корню
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_git_command(args: List[str], timeout: int = 30) -> Tuple[bool, str]:
    """
    Выполняет git-команду.
    
    Args:
        args: Аргументы для git (например ['pull', 'origin', 'main'])
        timeout: Таймаут в секундах
    
    Returns:
        (success, output) - успех и вывод команды
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=get_project_root(),
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=timeout
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return success, output.strip()
    except subprocess.TimeoutExpired:
        return False, "⏱ Превышено время ожидания команды"
    except FileNotFoundError:
        return False, "❌ Git не установлен или не найден в PATH"
    except Exception as e:
        logger.error(f"Ошибка выполнения git: {e}")
        return False, f"❌ Ошибка: {e}"


def check_git_available() -> bool:
    """
    Проверяет доступность git.
    
    Returns:
        True если git доступен
    """
    success, _ = run_git_command(['--version'])
    return success


def get_current_commit() -> Optional[str]:
    """
    Получает хеш текущего коммита.
    
    Returns:
        Короткий хеш коммита или None при ошибке
    """
    success, output = run_git_command(['rev-parse', '--short', 'HEAD'])
    return output if success else None


def get_current_branch() -> Optional[str]:
    """
    Получает имя текущей ветки.
    
    Returns:
        Имя ветки или None при ошибке
    """
    success, output = run_git_command(['branch', '--show-current'])
    return output if success else None


def get_remote_url() -> Optional[str]:
    """
    Получает URL удалённого репозитория origin.
    
    Returns:
        URL или None при ошибке
    """
    success, output = run_git_command(['remote', 'get-url', 'origin'])
    return output if success else None


def set_remote_url(url: str) -> Tuple[bool, str]:
    """
    Устанавливает URL удалённого репозитория origin.
    
    Args:
        url: Новый URL репозитория
    
    Returns:
        (success, message)
    """
    # Проверяем, есть ли remote origin
    success, _ = run_git_command(['remote', 'get-url', 'origin'])
    
    if success:
        # Меняем существующий
        return run_git_command(['remote', 'set-url', 'origin', url])
    else:
        # Добавляем новый
        return run_git_command(['remote', 'add', 'origin', url])


def get_pending_commits_list() -> Tuple[bool, List[Dict[str, str]]]:
    """
    Получает список коммитов между HEAD и origin/branch.
    
    Выполняет git fetch перед проверкой.
    
    Returns:
        (success, commits) — список словарей [{"hash": str, "message": str}, ...]
        от старого к новому (--reverse)
    """
    # Получаем обновления с сервера
    success, output = run_git_command(['fetch', 'origin'], timeout=60)
    if not success:
        logger.error(f"Ошибка fetch при получении списка коммитов: {output}")
        return False, []
    
    # Получаем текущую ветку
    branch = get_current_branch()
    if not branch:
        logger.error("Не удалось определить текущую ветку")
        return False, []
    
    # Проверяем, существует ли удаленная ветка
    success, _ = run_git_command(['rev-parse', '--verify', f'origin/{branch}'])
    if not success:
        logger.warning(f"Удаленная ветка origin/{branch} не найдена. Обновления недоступны.")
        return True, []
        
    # Получаем список коммитов от старого к новому
    success, output = run_git_command([
        'log', f'HEAD..origin/{branch}', '--format=%H|%s', '--reverse'
    ])
    
    if not success:
        logger.error(f"Ошибка получения списка коммитов: {output}")
        return False, []
    
    if not output.strip():
        return True, []
    
    commits = []
    for line in output.strip().split('\n'):
        if '|' in line:
            parts = line.split('|', 1)
            commits.append({
                "hash": parts[0].strip(),
                "message": parts[1].strip()
            })
    
    logger.debug(f"Найдено {len(commits)} ожидающих коммитов")
    return True, commits


def find_first_blocking_commit(commits: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Находит первый блокирующий коммит в списке.
    
    Блокирующий коммит — тот, чьё сообщение начинается с '!'.
    Чистая функция, никаких git-операций.
    
    Args:
        commits: Список коммитов из get_pending_commits_list()
    
    Returns:
        Словарь {"hash": ..., "message": ...} или None если блокирующих нет
    """
    for commit in commits:
        if commit.get("message", "").startswith("!"):
            return commit
    return None


def pull_to_commit(commit_hash: str) -> Tuple[bool, str]:
    """
    Обновляет код до конкретного коммита через git reset --hard.
    
    НЕ делает перезапуск — это ответственность вызывающего кода.
    
    Args:
        commit_hash: Полный хеш коммита для обновления
    
    Returns:
        (success, message) — результат операции
    """
    try:
        success, output = run_git_command(['reset', '--hard', commit_hash], timeout=120)
        if not success:
            logger.error(f"Ошибка pull_to_commit({commit_hash}): {output}")
            return False, f"❌ Ошибка обновления до коммита {commit_hash[:8]}:\n{output}"
        
        commit_info = get_last_commit_info('HEAD')
        logger.info(f"✅ Успешно обновлено до блокирующего коммита {commit_hash[:8]}")
        return True, f"✅ Обновление до блокирующего коммита завершено!\n\n🔹 Текущий коммит:\n<pre>{commit_info}</pre>"
    except Exception as e:
        logger.error(f"Исключение в pull_to_commit({commit_hash}): {e}", exc_info=True)
        return False, f"❌ Критическая ошибка: {e}"


def check_for_updates() -> Tuple[bool, int, str, bool, Optional[Dict[str, str]], bool]:
    """
    Проверяет наличие обновлений на сервере.
    
    Returns:
        (success, commits_behind, log_text, has_blocking, blocking_commit, is_beta_only)
        - success: успешно ли выполнена проверка
        - commits_behind: количество коммитов позади
        - log_text: лог новых коммитов или сообщение об ошибке
        - has_blocking: есть ли блокирующий коммит среди ожидающих
        - blocking_commit: словарь {"hash": ..., "message": ...} первого блокирующего или None
        - is_beta_only: все ли ожидающие коммиты являются бета-версиями (начинаются с '?')
    """
    # Получаем список ожидающих коммитов (внутри делает fetch)
    success, pending_commits = get_pending_commits_list()
    if not success:
        return False, 0, "Ошибка получения списка коммитов", False, None, False
    
    commits_behind = len(pending_commits)
    
    if commits_behind == 0:
        return True, 0, "✅ Бот уже обновлён до последней версии", False, None, False
    
    # Ищем блокирующий коммит
    blocking_commit = find_first_blocking_commit(pending_commits)
    has_blocking = blocking_commit is not None
    
    # Проверяем на бета-версии (начинаются с '?')
    is_beta_only = all(c.get("message", "").startswith("?") for c in pending_commits)
    
    if has_blocking:
        logger.info(f"⚠️ Обнаружен блокирующий коммит: {blocking_commit['hash'][:8]} — {blocking_commit['message']}")
    
    # Получаем текущую ветку для лога
    branch = get_current_branch() or 'main'
    
    # Получаем лог новых коммитов
    success_log, log_output = run_git_command([
        'log', '--format=%h %B', f'HEAD..origin/{branch}', '-n', '10'
    ])
    
    log_text = f"📦 Доступно обновлений: {commits_behind}\n\n"
    if success_log and log_output:
        log_text += "Последние изменения:\n<pre>" + log_output + "</pre>"
    
    return True, commits_behind, log_text, has_blocking, blocking_commit, is_beta_only


def pull_updates() -> Tuple[bool, str]:
    """
    Выполняет git pull для обновления кода.
    
    Returns:
        (success, message) - сообщение содержит информацию о коммите
    """
    success, status = run_git_command(['status', '--porcelain'])
    if success and status.strip():
        return False, "❌ Есть локальные изменения. Сделайте commit или stash перед обновлением."
    
    success, output = run_git_command(['pull', 'origin'], timeout=120)
    
    if not success:
        if 'conflict' in output.lower():
            return False, "❌ Конфликт слияния. Требуется ручное разрешение."
        return False, f"❌ Ошибка обновления:\n{output}"
    
    commit_info = get_last_commit_info('HEAD')
    return True, f"✅ Обновление успешно!\n\n🔹 Последний коммит:\n<pre>{commit_info}</pre>"


def force_pull_updates() -> Tuple[bool, str]:
    """
    Выполняет принудительный git fetch и reset, полностью перезаписывая локальные изменения.
    
    # force_pull намеренно игнорирует блокирующие маркеры — это аварийная функция.
    # НЕ вызывает pull_to_commit() и НЕ проверяет наличие блокирующих коммитов.
    # Всегда обновляет до последней версии origin/branch.
    
    Returns:
        (success, message)
    """
    # Скачиваем все изменения
    success, output = run_git_command(['fetch', 'origin'], timeout=120)
    if not success:
        return False, f"❌ Ошибка fetch:\n{output}"
    
    branch = get_current_branch()
    if not branch:
        branch = "main"
        
    # Принудительно сбрасываем на удалённую ветку — блокирующие маркеры игнорируются
    success, output = run_git_command(['reset', '--hard', f'origin/{branch}'], timeout=120)
    if not success:
        return False, f"❌ Ошибка принудительного обновления:\n{output}"
        
    commit_info = get_last_commit_info('HEAD')
    return True, f"✅ Принудительное обновление успешно завершено!\nВсе файлы перезаписаны из репозитория.\n\n🔹 Актуальный коммит:\n<pre>{commit_info}</pre>"


def get_last_commit_info(revision: str = 'HEAD') -> str:
    """Получает информацию о последнем коммите."""
    success, output = run_git_command([
        'log', '--format=%h %B', '-n', '1', revision
    ])
    if success and output:
        return output
    return "Не удалось получить информацию о последнем коммите"


def get_previous_commits_info(limit: int = 5, revision: str = 'HEAD') -> str:
    """Получает предыдущие коммиты, пропуская последний."""
    success, output = run_git_command([
        'log', '--format=%h %B', '--skip=1', '-n', str(limit), revision
    ])
    if success and output:
        return output
    return "Нет предыдущих коммитов"


def restart_bot() -> None:
    """
    Перезапускает бота, заменяя текущий процесс.
    
    Использует os.execv для замены текущего процесса новым.
    """
    logger.info("🔄 Перезапуск бота...")
    
    # Получаем путь к Python и аргументы запуска
    python = sys.executable
    script = os.path.join(get_project_root(), 'main.py')
    
    # Заменяем текущий процесс новым
    os.execv(python, [python, script])
