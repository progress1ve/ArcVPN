// Тонкая обёртка над Telegram WebApp SDK. Вне Telegram (например при локальной
// разработке в браузере) tg === undefined — все вызовы становятся no-op, а
// initData пустой (API ответит 401, экран покажет состояние «открой из бота»).

export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

export function initTelegram() {
  if (!tg) return
  tg.ready()
  tg.expand()
  // Закрываем приложение только осознанно — гасим случайный свайп вниз.
  tg.disableVerticalSwipes?.()
}

export function getInitData() {
  return tg?.initData || ''
}

export function getUser() {
  return tg?.initDataUnsafe?.user || null
}

// Лёгкая тактильная отдача на ключевых действиях.
export function haptic(kind = 'light') {
  const h = tg?.HapticFeedback
  if (!h) return
  if (kind === 'success' || kind === 'error' || kind === 'warning') {
    h.notificationOccurred(kind)
  } else {
    h.impactOccurred(kind)
  }
}

// Внешняя ссылка (App Store, сайт, deeplink happ://)
export function openExternal(url) {
  if (!url) return
  if (tg?.openLink && /^https?:/i.test(url)) {
    tg.openLink(url)
  } else {
    window.location.href = url
  }
}

// Ссылка внутрь Telegram (t.me/...) — открывает бот/канал и сворачивает Mini App
export function openTelegram(url) {
  if (!url) return
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(url)
  } else {
    window.open(url, '_blank')
  }
}

export function setHeaderColor(hex) {
  tg?.setHeaderColor?.(hex)
  tg?.setBackgroundColor?.(hex)
}
