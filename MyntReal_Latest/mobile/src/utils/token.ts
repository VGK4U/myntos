/**
 * Shared Token Resolution Utility for MyntOS Mobile
 * DC Protocol: DC_MOBILE_TOKEN_UTIL_001
 * Safely resolves authentication token across staff, partner, and member logins.
 */

export function getStoredToken(): string {
  if (typeof window === 'undefined') return '';
  return (
    localStorage.getItem('vgk_token') ||
    localStorage.getItem('auth_token') ||
    localStorage.getItem('staff_token') ||
    localStorage.getItem('token') ||
    localStorage.getItem('access_token') ||
    sessionStorage.getItem('staff_token') ||
    sessionStorage.getItem('token') ||
    sessionStorage.getItem('access_token') ||
    ''
  );
}

export function getStoredUser(): any {
  if (typeof window === 'undefined') return {};
  try {
    const raw =
      localStorage.getItem('staff_user') ||
      localStorage.getItem('user') ||
      localStorage.getItem('vgk_partner') ||
      sessionStorage.getItem('staff_user') ||
      '{}';
    return JSON.parse(raw);
  } catch (e) {
    return {};
  }
}
