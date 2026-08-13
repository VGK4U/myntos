import { useStaffAuth } from '@/contexts/StaffAuthContext';

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

export function useStaffFetch() {
  const { token, logout } = useStaffAuth();

  const handleSilentRefresh = async (): Promise<string | null> => {
    if (isRefreshing) return refreshPromise;
    
    const currentToken = localStorage.getItem('staff_token');
    if (!currentToken) return null;

    isRefreshing = true;
    
    refreshPromise = (async () => {
      try {
        const response = await fetch('/api/v1/staff/auth/refresh', {
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
    // 100% Coverage: Automatically attach token
    let currentToken = localStorage.getItem('staff_token');
    
    const headers = new Headers(options.headers || {});
    if (currentToken && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${currentToken}`);
    }

    let response = await fetch(url, { ...options, headers });

    // Handle 401 Expiration transparently
    if (response.status === 401) {
      const newToken = await handleSilentRefresh();
      
      if (newToken) {
        headers.set('Authorization', `Bearer ${newToken}`);
        response = await fetch(url, { ...options, headers });
      } else {
        logout();
      }
    }

    return response;
  };

  return { staffFetch };
}
