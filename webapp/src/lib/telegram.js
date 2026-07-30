// Тонкая обёртка над Telegram WebApp SDK. Вне Telegram (например при локальной
// разработке в браузере) tg === undefined — все вызовы становятся no-op, а
// initData пустой (API ответит 401, экран покажет состояние «открой из бота»).

export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

function syncSafeArea() {
  if (typeof document === 'undefined') return
  const safe = tg?.safeAreaInset || {}
  const content = tg?.contentSafeAreaInset || safe
  const root = document.documentElement
  root.style.setProperty('--tg-safe-top', `${Math.max(0, Number(safe.top) || 0)}px`)
  root.style.setProperty('--tg-safe-bottom', `${Math.max(0, Number(safe.bottom) || 0)}px`)
  root.style.setProperty('--tg-content-safe-top', `${Math.max(0, Number(content.top) || 0)}px`)
  root.style.setProperty('--tg-content-safe-bottom', `${Math.max(0, Number(content.bottom) || 0)}px`)
}

export function initTelegram() {
  if (!tg) return
  tg.ready()
  tg.expand()
  tg.setHeaderColor?.('#02050b')
  tg.setBackgroundColor?.('#02050b')
  tg.setBottomBarColor?.('#02050b')
  syncSafeArea()
  tg.onEvent?.('safeAreaChanged', syncSafeArea)
  tg.onEvent?.('contentSafeAreaChanged', syncSafeArea)
  tg.onEvent?.('viewportChanged', syncSafeArea)
  // Закрываем приложение только осознанно — гасим случайный свайп вниз.
  tg.disableVerticalSwipes?.()
  // BotFather Fullscreen — основной launch mode. Этот вызов страхует старые
  // direct-link/inline-точки входа в клиентах с Bot API 8.0+.
  try {
    if (tg.isVersionAtLeast?.('8.0') && !tg.isFullscreen) tg.requestFullscreen?.()
  } catch {}
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

export function selectionHaptic() {
  tg?.HapticFeedback?.selectionChanged?.()
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

export function openPayment(url) {
  if (!url) return
  haptic('medium')
  if (tg?.openLink) tg.openLink(url)
  else window.open(url, '_blank', 'noopener,noreferrer')
}

let activeBackHandler = null

export function setNativeBackHandler(handler = null) {
  if (!tg?.BackButton) return
  if (activeBackHandler) tg.BackButton.offClick(activeBackHandler)
  activeBackHandler = typeof handler === 'function' ? handler : null
  if (activeBackHandler) {
    tg.BackButton.onClick(activeBackHandler)
    tg.BackButton.show()
  } else {
    tg.BackButton.hide()
  }
}

// Ссылка внутрь Telegram (t.me/...) — открывает бот/канал и закрывает Mini App
export function openTelegram(url) {
  if (!url) return
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(url)
    // Закрываем WebApp — пользователь видит бота в чате
    tg.close()
  } else {
    window.open(url, '_blank')
  }
}

export function setHeaderColor(hex) {
  tg?.setHeaderColor?.(hex)
  tg?.setBackgroundColor?.(hex)
}
