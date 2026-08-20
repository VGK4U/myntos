import axios from 'axios';

// Base API instance
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getApiUrl = () => API_BASE_URL;

// Helper to determine portal type from path
const getPortalType = (pathname: string) => {
  if (pathname.startsWith('/staff')) return 'staff';
  if (pathname.startsWith('/member')) return 'member';
  if (pathname.startsWith('/vendor')) return 'vendor';
  if (pathname.startsWith('/superadmin')) return 'superadmin';
  return null;
};

// Request Interceptor to attach correct JWT token
api.interceptors.request.use(
  (config) => {
    // Only run in the browser
    if (typeof window !== 'undefined') {
      const portal = getPortalType(window.location.pathname);
      if (portal) {
        const token = localStorage.getItem(`${portal}_token`);
        if (token) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor to handle 401s globally
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Auto-logout if token is expired/invalid
      if (typeof window !== 'undefined') {
        const portal = getPortalType(window.location.pathname);
        if (portal && !window.location.pathname.endsWith('/login')) {
          localStorage.removeItem(`${portal}_token`);
          localStorage.removeItem(`${portal}_user`);
          window.location.assign(`${window.location.origin}/${portal}/login`);
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
