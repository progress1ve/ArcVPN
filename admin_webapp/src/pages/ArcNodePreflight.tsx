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

export default function ArcNodePreflight() {
  const [open, setOpen] = useState(false);
  const [host, setHost] = useState('');
  const [port, setPort] = useState('22');
  const [username, setUsername] = useState('root');
  const [password, setPassword] = useState('');
  const [expectedFingerprint, setExpectedFingerprint] = useState('');
  const [observed, setObserved] = useState<HostKey | null>(null);
  const [result, setResult] = useState<Preflight | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function inspectKey() {
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
      setError(cause instanceof Error ? cause.message : 'SSH недоступен');
    } finally {
      setBusy(false);
    }
  }
  async function preflight() {
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
        preset: 'full',
      });
      setResult(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Проверка не удалась');
    } finally {
      setPassword('');
      setBusy(false);
    }
  }
  return (
    <section className="rounded-xl border border-dark-700 bg-dark-800/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-dark-100">Проверить новый сервер</h3>
          <p className="mt-1 text-xs text-dark-400">
            Проверка SSH-доступа и предварительного состава. Сервер не добавляется и не публикуется.
          </p>
        </div>
        <button
          onClick={() => setOpen(!open)}
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
                onChange={(event) => {
                  setHost(event.target.value);
                  setObserved(null);
                  setResult(null);
                }}
                placeholder="203.0.113.10"
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
            <label className="text-xs text-dark-300">
              SSH порт
              <input
                value={port}
                onChange={(event) => setPort(event.target.value)}
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
                onChange={(event) => setExpectedFingerprint(event.target.value)}
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
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-sm text-dark-100"
              />
            </label>
            <button
              disabled={busy || !host.trim() || !expectedFingerprint.trim() || !password}
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
              <h4 className="font-semibold text-success-400">SSH-проверка пройдена</h4>
              <p className="mt-1 text-xs text-dark-400">
                {result.host}:{result.port}. Пароль очищен из формы; установка не запускалась.
              </p>
              <pre className="mt-3 overflow-auto whitespace-pre-wrap text-xs text-dark-200">
                {result.system}
              </pre>
            </div>
          )}
          <div className="rounded-lg bg-dark-900/60 p-4">
            <h4 className="text-sm font-semibold text-dark-100">
              Предварительный состав полного preset
            </h4>
            <ul className="mt-2 grid gap-1 text-xs text-dark-300 sm:grid-cols-2">
              <li>Обычная Reality-нода и отдельные ключи</li>
              <li>Мост Москва → новая нода</li>
              <li>Мост новая нода → Москва для YouTube</li>
              <li>AutoSelect и YouTube pool</li>
              <li>Отдельный CDN/XHTTP путь</li>
              <li>Скрытый canary и реальные туннельные gates</li>
            </ul>
            <p className="mt-3 text-xs text-warning-400">
              Перед установкой потребуется точная таблица Host/SNI, путей, порядка и отката. Текущая
              проверка ничего не устанавливает.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
