import { useStaffAuth } from '@/contexts/StaffAuthContext';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

/**
 * Resolves a URL to the correct backend base.
 * - If the URL starts with 'http', it's already absolute → use as-is
 * - Otherwise, it's a backend relative path → prepend API_BASE_URL
 */
function resolveBackendUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  return `${API_BASE_URL}${url.startsWith('/') ? url : '/' + url}`;
}

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

export function useStaffFetch() {
  const { logout } = useStaffAuth();

  const handleSilentRefresh = async (): Promise<string | null> => {
    if (isRefreshing) return refreshPromise;
    
    const currentToken = localStorage.getItem('staff_token');
    if (!currentToken) return null;

    isRefreshing = true;
    
    refreshPromise = (async () => {
      try {
        const response = await fetch(resolveBackendUrl('/api/v1/staff/auth/refresh'), {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${currentToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          if (data.access_token) {
            localStorage.setItem('staff_token', data.access_token);
            document.cookie = `staff_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
            return data.access_token;
          }
        }
        
        // If refresh fails, log them out
        if (response.status === 401) {
          logout();
        }
        return null;
      } catch (error) {
        console.error('[DC_TOKEN] Refresh network error:', error);
        return null;
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  };

  const staffFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
    // Resolve relative paths to the backend base URL
    const resolvedUrl = resolveBackendUrl(url);

    // 100% Coverage: Automatically attach token
    const currentToken = localStorage.getItem('staff_token');
    
    const headers = new Headers(options.headers || {});
    if (!headers.has('Content-Type') && options.body) {
      headers.set('Content-Type', 'application/json');
    }
    if (currentToken && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${currentToken}`);
    }

    let response = await fetch(resolvedUrl, { ...options, headers });

    // Handle 401 Expiration transparently
    if (response.status === 401) {
      const newToken = await handleSilentRefresh();
      
      if (newToken) {
        headers.set('Authorization', `Bearer ${newToken}`);
        response = await fetch(resolvedUrl, { ...options, headers });
      } else {
        logout();
      }
    }

    return response;
  };

  return { staffFetch };
}
