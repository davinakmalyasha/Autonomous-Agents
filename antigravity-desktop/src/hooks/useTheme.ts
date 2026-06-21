import { type Theme } from '../types';

export function getSystemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

export function getStoredTheme(): Theme {
  const stored = localStorage.getItem('app-theme') as Theme | null;
  if (stored === 'dark' || stored === 'light') return stored;
  return getSystemTheme();
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === 'light') {
    root.classList.add('light');
  } else {
    root.classList.remove('light');
  }
}

export function toggleTheme(current: Theme): Theme {
  const next: Theme = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem('app-theme', next);
  applyTheme(next);
  return next;
}
