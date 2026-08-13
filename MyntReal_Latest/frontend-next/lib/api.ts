import axios from 'axios';

// Base API instance
const api = axios.create({
  baseURL: 'http://127.0.0.1:5000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getApiUrl = () => 'http://127.0.0.1:5000';

// Request Interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    // Only run in the browser
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('staff_token');
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
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
        localStorage.removeItem('staff_token');
        if (window.location.pathname !== '/login' && window.location.pathname.startsWith('/staff')) {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
