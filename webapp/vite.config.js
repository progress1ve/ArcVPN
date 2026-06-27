import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// Mini App раздаётся Flask-сервисом под /app/, поэтому base = '/app/'.
// Сборка кладётся в ../webapp_dist (коммитится в репо — на сервере Node не нужен).
export default defineConfig({
  base: '/app/',
  plugins: [svelte()],
  build: {
    outDir: '../webapp_dist',
    emptyOutDir: true,
    target: 'es2018',
  },
})
