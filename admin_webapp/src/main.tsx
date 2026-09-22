import React from 'react';
import ReactDOM from 'react-dom/client';
import { installEncodingSurrogateGuard } from './utils/installEncodingSurrogateGuard';
import { i18nReady } from './i18n';
import './styles/globals.css';
import Root from './arcvpn/ArcAdminRoot';

installEncodingSurrogateGuard();

async function bootstrap() {
  await i18nReady;
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <Root />
    </React.StrictMode>,
  );
}

void bootstrap();
