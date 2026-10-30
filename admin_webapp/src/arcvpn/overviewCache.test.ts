import { afterEach, describe, expect, it, vi } from 'vitest';
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe('overview telemetry freshness', () => {
  it('shares concurrent reads and refreshes after the bounded cache window', async () => {
    vi.resetModules(); vi.stubEnv('DEV', false);
    const now = vi.spyOn(Date, 'now').mockReturnValue(1000);
    const fetcher = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ online: 2 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ online: 4 }) });
    vi.stubGlobal('fetch', fetcher);
    const { getOverview } = await import('./api');
    const first = getOverview(); expect(getOverview()).toBe(first);
    expect((await first).online).toBe(2); expect(fetcher).toHaveBeenCalledTimes(1);
    now.mockReturnValue(61000);
    expect((await getOverview()).online).toBe(4); expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it('retries a failed request instead of caching its rejection', async () => {
    vi.resetModules(); vi.stubEnv('DEV', false);
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ online: 0 }) }));
    const { getOverview } = await import('./api');
    await expect(getOverview()).rejects.toThrow('offline');
    expect((await getOverview()).online).toBe(0);
  });
});
