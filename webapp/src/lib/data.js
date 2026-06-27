import { writable } from 'svelte/store'
import { fetchStatus, fetchTariffs, fetchReferral } from './api.js'

const initial = () => ({ loading: false, error: null, data: null, loaded: false })

export const status = writable(initial())
export const tariffs = writable(initial())
export const referral = writable(initial())

async function load(store, fetcher, { force = false } = {}) {
  let snapshot
  store.update((s) => {
    snapshot = s
    return { ...s, loading: true, error: null }
  })
  if (snapshot.loaded && !force) {
    store.update((s) => ({ ...s, loading: false }))
    return
  }
  try {
    const data = await fetcher()
    store.set({ loading: false, error: null, data, loaded: true })
  } catch (err) {
    store.set({
      loading: false,
      error: err.code === 401 ? 'unauthorized' : 'error',
      data: null,
      loaded: false,
    })
  }
}

export const loadStatus = (opts) => load(status, fetchStatus, opts)
export const loadTariffs = (opts) => load(tariffs, fetchTariffs, opts)
export const loadReferral = (opts) => load(referral, fetchReferral, opts)
