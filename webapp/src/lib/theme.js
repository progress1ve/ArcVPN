// Тема приложения. По умолчанию тёмная (фирменная). Пользователь может
// переключить на светлую в Профиле — выбор запоминается в localStorage.
import { writable } from 'svelte/store'
import { setHeaderColor } from './telegram.js'

const KEY = 'arc-theme'
const BG = { dark: '#07090f', light: '#eceef4' }

function read() {
  try {
    // Явный override через ?theme=light|dark (предпросмотр/диплинк)
    const q = new URLSearchParams(location.search).get('theme')
    if (q === 'light' || q === 'dark') return q
    const saved = localStorage.getItem(KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {}
  return 'dark'
}

function apply(value) {
  document.documentElement.setAttribute('data-theme', value)
  setHeaderColor(BG[value])
}

export const theme = writable(read())

theme.subscribe((value) => {
  apply(value)
  try {
    localStorage.setItem(KEY, value)
  } catch {}
})

export function toggleTheme() {
  theme.update((t) => (t === 'dark' ? 'light' : 'dark'))
}
