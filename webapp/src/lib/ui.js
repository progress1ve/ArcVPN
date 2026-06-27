import { writable } from 'svelte/store'
import { haptic } from './telegram.js'

export const toastMsg = writable('')
let timer

export function toast(message) {
  toastMsg.set(message)
  clearTimeout(timer)
  timer = setTimeout(() => toastMsg.set(''), 2200)
}

// Копирование с фолбэком для старых WebView. По успеху — тост и тактильная отдача.
export async function copyText(text, label = 'Скопировано') {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
    } catch {}
    document.body.removeChild(ta)
  }
  haptic('success')
  toast(label)
}
