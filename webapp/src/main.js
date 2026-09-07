import './app.css'
import Root from './Root.svelte'
import { initTelegram } from './lib/telegram.js'

initTelegram()

const app = new Root({
  target: document.getElementById('app'),
})

export default app
