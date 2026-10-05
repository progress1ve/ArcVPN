import React from 'react';
import ReactDOM from 'react-dom/client';
import { MotionConfig } from 'framer-motion';
import { PlatformContext } from '@/platform/PlatformContext';
import { createWebAdapter } from '@/platform/adapters/WebAdapter';
import ArcPartnerCabinet from './arcvpn/ArcPartnerCabinet';
import './styles/globals.css';

// Reuse admin UI primitives with the web adapter, without admin auth or routes.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <PlatformContext.Provider value={createWebAdapter()}>
      <MotionConfig reducedMotion="user">
        <ArcPartnerCabinet />
      </MotionConfig>
    </PlatformContext.Provider>
  </React.StrictMode>,
);
