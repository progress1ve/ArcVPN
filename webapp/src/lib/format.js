// Форматтеры для отображения. Русские склонения, байты, даты.

export function plural(n, one, few, many) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}

export function formatBytes(bytes) {
  bytes = Number(bytes) || 0
  if (bytes <= 0) return '0 ГБ'
  const gb = bytes / 1024 ** 3
  if (gb >= 1024) return `${(gb / 1024).toFixed(2)} ТБ`
  if (gb >= 10) return `${Math.round(gb)} ГБ`
  if (gb >= 1) return `${gb.toFixed(1)} ГБ`
  const mb = bytes / 1024 ** 2
  return `${Math.max(1, Math.round(mb))} МБ`
}

// Сколько дней осталось до unix-времени истечения (минимум 0).
export function daysLeft(expiresUnix) {
  if (!expiresUnix) return 0
  const now = Date.now() / 1000
  const diff = expiresUnix - now
  if (diff <= 0) return 0
  return Math.ceil(diff / 86400)
}

export function formatDate(expiresUnix) {
  if (!expiresUnix) return '—'
  const d = new Date(expiresUnix * 1000)
  return d.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export function daysWord(n) {
  return plural(n, 'день', 'дня', 'дней')
}

// Глагол согласования: «остался 1 день» / «осталось 5 дней» / «осталось 3 дня».
export function leftVerb(n) {
  return n % 10 === 1 && n % 100 !== 11 ? 'остался' : 'осталось'
}

export function peopleWord(n) {
  return plural(n, 'человек', 'человека', 'человек')
}

export function deviceWord(n) {
  return plural(n, 'устройство', 'устройства', 'устройств')
}

export function formatRub(rub) {
  return `${Math.round(Number(rub) || 0).toLocaleString('ru-RU')} ₽`
}

export function formatRubFromCents(cents) {
  return formatRub((Number(cents) || 0) / 100)
}
