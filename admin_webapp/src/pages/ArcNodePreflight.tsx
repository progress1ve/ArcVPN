import { useState } from 'react';

type HostKey = { fingerprint: string; algorithm: string };
type Preflight = { host: string; port: number; system: string; fingerprint: string };

async function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(String(data.error || `HTTP ${response.status}`));
  return data as T;
}

export default function ArcNodePreflight({ initialOpen = false }: { initialOpen?: boolean }) {
  const [open, setOpen] = useState(initialOpen);
  const [host, setHost] = useState('');
  const [port, setPort] = useState('22');
  const [username, setUsername] = useState('root');
  const [password, setPassword] = useState('');
  const [expectedFingerprint, setExpectedFingerprint] = useState('');
  const [observed, setObserved] = useState<HostKey | null>(null);
  const [result, setResult] = useState<Preflight | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [verified, setVerified] = useState(false);
  const errors: Record<string, string> = {
    ssh_auth_failed: 'Сервер не принял логин или пароль.',
    ssh_host_key_mismatch: 'SSH-ключ изменился. Повторно сверьте отпечаток через провайдера.',
    invalid_ssh_target: 'Укажите публичный IP, допустимый порт и SSH-пользователя.',
    ssh_unavailable: 'Нет SSH-соединения. Проверьте IP, порт и доступность сервера.',
    ssh_fingerprint_required: 'Нужен независимо подтверждённый SSH-отпечаток.',
    admin_forbidden: 'Проверка серверов доступна владельцу.',
    admin_origin_forbidden: 'Откройте проверку на основном сайте ArcVPN.',
  };
  function resetTarget() {
    setObserved(null);
    setResult(null);
    setExpectedFingerprint('');
    setPassword('');
    setVerified(false);
    setError('');
  }
  async function inspectKey() {
    if (busy) return;
    setVerified(false);
    setBusy(true);
    setError('');
    setObserved(null);
    setResult(null);
    try {
      const data = await post<HostKey>('/api/admin/nodes/ssh-host-key', {
        host: host.trim(),
        port: Number(port),
      });
      setObserved(data);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? errors[cause.message] || 'Не удалось прочитать SSH-ключ. Повторите проверку.'
          : 'SSH недоступен',
      );
    } finally {
      setBusy(false);
    }
  }
  async function preflight() {
    if (busy || !verified) return;
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const data = await post<Preflight>('/api/admin/nodes/preflight', {
        host: host.trim(),
        port: Number(port),
        username: username.trim(),
        password,
        expected_fingerprint: expectedFingerprint.trim(),
        preset: 'direct',
      });
      setResult(data);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? errors[cause.message] || 'Серверная проверка не удалась. Повторите попытку.'
          : 'Проверка не удалась',
      );
    } finally {
      setPassword('');
      setBusy(false);
    }
  }
  return (
    <section className="rounded-xl border border-dark-700 bg-dark-800/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-dark-100">Проверить новый сервер</h2>
          <p className="mt-1 text-xs text-dark-400">
            Проверьте доступ, ОС и ресурсы перед добавлением ноды.
          </p>
        </div>
        <button
          onClick={() => {
            setOpen(!open);
            setPassword('');
          }}
          disabled={busy}
          aria-expanded={open}
          className="rounded-lg bg-accent-500/15 px-4 py-2 text-sm font-medium text-accent-300 hover:bg-accent-500/25"
        >
          {open ? 'Свернуть' : 'Начать проверку'}
        </button>
      </div>
      {open && (
        <div className="mt-5 space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="text-xs text-dark-300">
              Публичный IP
              <input
                value={host}
                disabled={busy}
                onChange={(event) => {
                  resetTarget();
                  setHost(event.target.value);
                }}
                placeholder="203.0.113.10"
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
            <label className="text-xs text-dark-300">
              SSH порт
              <input
                value={port}
                disabled={busy}
                onChange={(event) => {
                  resetTarget();
                  setPort(event.target.value);
                }}
                type="number"
                min="1"
                max="65535"
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
            <label className="text-xs text-dark-300">
              Пользователь
              <input
                value={username}
                disabled={busy}
                onChange={(event) => setUsername(event.target.value)}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
          </div>
          <button
            disabled={busy || !host.trim()}
            onClick={inspectKey}
            className="rounded-lg border border-dark-600 px-4 py-2 text-sm text-dark-200 disabled:opacity-50"
          >
            Показать SSH fingerprint
          </button>
          {observed && (
            <div className="rounded-lg border border-warning-500/25 bg-warning-500/5 p-4 text-sm">
              <p className="text-dark-300">Сервер предъявил {observed.algorithm}:</p>
              <code className="mt-2 block break-all text-accent-300">{observed.fingerprint}</code>
              <p className="mt-3 text-warning-400">
                Сравните с fingerprint в консоли провайдера или на самом VPS. Совпадение с числом
                выше без независимой сверки не подтверждает владельца.
              </p>
            </div>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void preflight();
            }}
            className="grid gap-3 md:grid-cols-2"
          >
            <label className="text-xs text-dark-300">
              Подтверждённый SSH fingerprint
              <input
                value={expectedFingerprint}
                disabled={busy}
                onChange={(event) => {
                  setVerified(false);
                  setExpectedFingerprint(event.target.value);
                }}
                placeholder="SHA256:..."
                autoComplete="off"
                required
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
            <label className="text-xs text-dark-300">
              SSH пароль
              <input
                value={password}
                disabled={busy}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
            <label className="flex items-start gap-2 text-xs leading-relaxed text-dark-300 md:col-span-2">
              <input
                type="checkbox"
                checked={verified}
                disabled={busy || !expectedFingerprint.trim()}
                onChange={(event) => setVerified(event.target.checked)}
              />
              Я сверил SSH-отпечаток независимо в консоли провайдера.
            </label>
            <button
              disabled={
                busy || !host.trim() || !expectedFingerprint.trim() || !password || !verified
              }
              className="rounded-lg bg-accent-500 px-4 py-2 text-sm font-semibold text-dark-950 disabled:opacity-50 md:col-span-2"
            >
              {busy ? 'Проверяем…' : 'Проверить доступ и сервер'}
            </button>
          </form>
          {error && (
            <p role="alert" className="text-sm text-error-400">
              Проверка: {error}
            </p>
          )}
          {result && (
            <div className="rounded-lg border border-success-500/30 p-4">
              <h3 className="font-semibold text-success-400">SSH-проверка пройдена</h3>
              <p className="mt-1 text-xs text-dark-400">
                {result.host}:{result.port}. Пароль очищен из формы; установка не запускалась.
              </p>
              <pre className="mt-3 overflow-auto whitespace-pre-wrap text-xs text-dark-200">
                {result.system}
              </pre>
            </div>
          )}
          <div className="rounded-lg bg-dark-900/60 p-4">
            <h3 className="text-sm font-semibold text-dark-100">Что проверяет этот экран</h3>
            <ul className="mt-2 grid gap-1 text-xs text-dark-300 sm:grid-cols-2">
              <li>SSH-доступ и ключ сервера</li>
              <li>ОС и архитектуру</li>
              <li>Свободный диск и память</li>
              <li>Наличие RemnaNode, Docker и nginx</li>
            </ul>
            <p className="mt-3 text-xs text-warning-400">
              Установка и публикация ноды пока выполняются отдельным процессом. Этот экран только
              читает сведения с сервера. Пароль не сохраняется и очищается после проверки.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
