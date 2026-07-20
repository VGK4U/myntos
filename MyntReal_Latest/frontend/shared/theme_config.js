/**
 * STFP Protocol - Theme Configuration
 * Single source of truth for role-specific theming
 * DC Protocol compliant: No duplication, config-driven
 */

const BUILD_ID = process.env.FRONTEND_BUILD_ID || String(Date.now());

const ROLE_THEMES = {
  admin: {
    name: 'Admin',
    title: 'Admin Panel',
    gradient: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
    primary: '#1e40af',
    secondary: '#3b82f6',
    icon: 'fa-user-shield',
    sidebarHover: 'linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%)',
    sidebarActive: '#1e40af'
  },
  superadmin: {
    name: 'Super Admin',
    title: 'Super Admin',
    gradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    primary: '#6366f1',
    secondary: '#8b5cf6',
    icon: 'fa-crown',
    sidebarHover: 'linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%)',
    sidebarActive: '#6366f1'
  },
  finance: {
    name: 'Finance',
    title: 'Finance Admin',
    gradient: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
    primary: '#059669',
    secondary: '#10b981',
    icon: 'fa-coins',
    sidebarHover: 'linear-gradient(90deg, #059669 0%, #10b981 100%)',
    sidebarActive: '#059669'
  },
  rvz: {
    name: 'RVZ',
    title: 'RVZ Supreme',
    gradient: 'linear-gradient(135deg, #dc2626 0%, #f97316 100%)',
    primary: '#dc2626',
    secondary: '#f97316',
    icon: 'fa-shield-halved',
    sidebarHover: 'linear-gradient(90deg, #dc2626 0%, #f97316 100%)',
    sidebarActive: '#dc2626'
  },
  user: {
    name: 'User',
    title: 'User Dashboard',
    gradient: 'linear-gradient(135deg, #0891b2 0%, #06b6d4 100%)',
    primary: '#0891b2',
    secondary: '#06b6d4',
    icon: 'fa-user',
    sidebarHover: 'linear-gradient(90deg, #0891b2 0%, #06b6d4 100%)',
    sidebarActive: '#0891b2'
  }
};

module.exports = { ROLE_THEMES, BUILD_ID };
