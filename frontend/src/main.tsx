/**
 * Application entry point.
 *
 * Mount order:
 *   StrictMode → BrowserRouter → AuthProvider → App
 *
 * BrowserRouter must wrap AuthProvider so that useNavigate() works inside
 * AuthContext (navigate is called during login/logout).
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import App from './App';
import './crm.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
