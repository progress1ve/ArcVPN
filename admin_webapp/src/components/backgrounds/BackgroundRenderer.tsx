import { RenderBackground } from './BackgroundCanvas';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { brandingApi } from '@/api/branding';
import type { AnimationConfig } from '@/components/ui/backgrounds/types';
import { DEFAULT_ANIMATION_CONFIG } from '@/components/ui/backgrounds/types';
import { prefetchBackground } from '@/components/ui/backgrounds/registry';
import { validateConfig, getCachedConfig, setCachedConfig } from '@/utils/backgroundConfig';

// Prefetch the background JS chunk immediately based on localStorage cache.
const cachedConfig = getCachedConfig();
if (cachedConfig?.enabled && cachedConfig.type && cachedConfig.type !== 'none') {
  prefetchBackground(cachedConfig.type);
}

export function BackgroundRenderer() {
  const { data: config } = useQuery({
    queryKey: ['animation-config'],
    queryFn: async () => {
      const raw = await brandingApi.getAnimationConfig();
      const result = validateConfig(raw) ?? DEFAULT_ANIMATION_CONFIG;
      setCachedConfig(result);
      return result;
    },
    initialData: getCachedConfig() ?? undefined,
    initialDataUpdatedAt: 0,
    staleTime: 30_000,
  });

  const effectiveConfig = config ?? DEFAULT_ANIMATION_CONFIG;
  return <RenderBackground config={effectiveConfig} />;
}

export function StaticBackgroundRenderer({ config }: { config: AnimationConfig }) {
  const validated = useMemo(() => validateConfig(config), [config]);
  if (!validated) return null;
  return <RenderBackground config={validated} />;
}
