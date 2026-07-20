// Authentication Middleware
// Handles session management and role-based access control

// DC Protocol: Backend URL Configuration
// For VM deployments (single container), use internal localhost
// The backend runs on port 8000 in the same container
const BACKEND_URL_SERVER = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

// Active sessions in memory
const activeSessions = new Set();

// Session role cache for performance
const sessionRoleCache = new Map();

// Get user role from session token
function getUserRole(sessionToken) {
  if (!sessionToken) return null;
  
  const cached = sessionRoleCache.get(sessionToken);
  if (cached) {
    return cached.authLevel;
  }
  
  // Default fallback
  return 'User';
}

// Validate session with backend
async function validateSession(sessionToken) {
  if (!sessionToken) return null;
  
  // Check if already in active sessions
  if (activeSessions.has(sessionToken)) {
    return { valid: true, role: getUserRole(sessionToken) };
  }
  
  // Validate with backend
  try {
    const response = await fetch(BACKEND_URL_SERVER + '/api/v1/auth/me', {
      headers: { 'Authorization': 'Bearer ' + sessionToken }
    });
    
    if (response.ok) {
      const profileData = await response.json();
      if (profileData.success && profileData.data) {
        activeSessions.add(sessionToken);
        sessionRoleCache.set(sessionToken, {
          userId: profileData.data.id,
          authLevel: profileData.data.user_type || 'User'
        });
        return { valid: true, role: profileData.data.user_type || 'User', data: profileData.data };
      }
    }
  } catch (err) {
    console.error('Session validation error:', err);
  }
  
  return null;
}

// Add session to active sessions
function addSession(sessionToken, userId, authLevel) {
  activeSessions.add(sessionToken);
  sessionRoleCache.set(sessionToken, { userId, authLevel });
}

// Remove session (logout)
function removeSession(sessionToken) {
  activeSessions.delete(sessionToken);
  sessionRoleCache.delete(sessionToken);
}

// Check if user is logged in
function isLoggedIn(sessionToken) {
  return sessionToken && activeSessions.has(sessionToken);
}

module.exports = {
  activeSessions,
  sessionRoleCache,
  getUserRole,
  validateSession,
  addSession,
  removeSession,
  isLoggedIn,
  BACKEND_URL_SERVER
};
