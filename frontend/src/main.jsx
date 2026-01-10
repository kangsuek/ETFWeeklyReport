import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/index.css'

// React 렌더링 전에 테마 적용 확인
(function() {
  const STORAGE_KEY = 'app_settings';
  const DEFAULT_THEME = 'light';
  
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    let theme = DEFAULT_THEME;
    
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed && parsed.theme) {
        theme = parsed.theme;
      }
    }
    
    // 시스템 테마 감지
    function getSystemTheme() {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    
    // 실제 적용할 테마 계산
    function getEffectiveTheme(theme) {
      if (theme === 'system') {
        return getSystemTheme();
      }
      return theme;
    }
    
    // 테마 적용
    const effectiveTheme = getEffectiveTheme(theme);
    const root = document.documentElement;
    if (effectiveTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  } catch (error) {
    // Failed to apply theme - use default
  }
})();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
