import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { API_KEY_STORAGE } from './api/client.js';
import './index.css';

// Аварийный сброс X-Api-Key через URL: открой /?reset=1 — ключ удалится,
// параметр уберётся из адреса, появится экран ApiKeySetup.
if (new URLSearchParams(window.location.search).get('reset') === '1') {
  localStorage.removeItem(API_KEY_STORAGE);
  window.history.replaceState({}, '', window.location.pathname);
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
