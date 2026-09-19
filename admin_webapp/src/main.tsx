import React from 'react';
import ReactDOM from 'react-dom/client';
import { installEncodingSurrogateGuard } from './utils/installEncodingSurrogateGuard';
import './i18n';
import './styles/globals.css';
import Root from './arcvpn/ArcAdminRoot';

installEncodingSurrogateGuard();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
