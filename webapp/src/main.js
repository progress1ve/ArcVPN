import './app.css'
import App from './App.svelte'
import { initTelegram } from './lib/telegram.js'

initTelegram()

const app = new App({
  target: document.getElementById('app'),
})

export default app
