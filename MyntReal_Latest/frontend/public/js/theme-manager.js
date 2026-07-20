/**
 * Theme Manager - Dark/Light Mode Toggle
 * DC Protocol: DC_THEME_001
 * Handles theme switching with localStorage persistence
 */

const ThemeManager = (function() {
  const STORAGE_KEY = 'mnr_theme_preference';
  const DARK_CLASS = 'dark-theme';
  const LIGHT_CLASS = 'light-theme';
  
  function init() {
    const savedTheme = localStorage.getItem(STORAGE_KEY) || 'dark';
    applyTheme(savedTheme);
    console.log('[DC_THEME_001] Theme initialized:', savedTheme);
  }
  
  function applyTheme(theme) {
    const body = document.body;
    
    if (theme === 'dark') {
      body.classList.add(DARK_CLASS);
      body.classList.remove(LIGHT_CLASS);
    } else {
      body.classList.remove(DARK_CLASS);
      body.classList.add(LIGHT_CLASS);
    }
    
    document.querySelectorAll('.theme-toggle-icon').forEach(icon => {
      icon.className = theme === 'dark' 
        ? 'fas fa-moon theme-toggle-icon' 
        : 'fas fa-sun theme-toggle-icon';
    });
    
    document.querySelectorAll('.theme-toggle-text').forEach(text => {
      text.textContent = theme === 'dark' ? 'Dark Mode' : 'Light Mode';
    });
  }
  
  function toggle() {
    const currentTheme = localStorage.getItem(STORAGE_KEY) || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    localStorage.setItem(STORAGE_KEY, newTheme);
    applyTheme(newTheme);
    
    console.log('[DC_THEME_001] Theme toggled to:', newTheme);
    return newTheme;
  }
  
  function setTheme(theme) {
    if (theme !== 'dark' && theme !== 'light') {
      console.warn('[DC_THEME_001] Invalid theme:', theme);
      return;
    }
    
    localStorage.setItem(STORAGE_KEY, theme);
    applyTheme(theme);
    console.log('[DC_THEME_001] Theme set to:', theme);
  }
  
  function getCurrentTheme() {
    return localStorage.getItem(STORAGE_KEY) || 'dark';
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  return {
    init: init,
    toggle: toggle,
    setTheme: setTheme,
    getCurrentTheme: getCurrentTheme
  };
})();

if (typeof window !== 'undefined') {
  window.ThemeManager = ThemeManager;
}
