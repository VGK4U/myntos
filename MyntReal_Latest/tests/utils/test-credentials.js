const TEST_PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD || 'Test@123';

const TEST_CREDENTIALS = {
  staff: {
    employeeId: process.env.TEST_STAFF_EMPLOYEE_ID || 'MR10001',
    password: process.env.TEST_STAFF_PASSWORD || 'Test@123',
    loginType: 'staff',
    description: 'Regular Staff Employee'
  },
  rvz: {
    employeeId: process.env.TEST_RVZ_USERNAME || 'MR10001',
    password: process.env.TEST_RVZ_PASSWORD || 'Test@123',
    loginType: 'staff',
    description: 'RVZ Supreme Admin (VGK4U)'
  },
  superAdmin: {
    employeeId: process.env.TEST_SUPERADMIN_USERNAME || 'MR10001',
    password: process.env.TEST_SUPERADMIN_PASSWORD || 'Test@123',
    loginType: 'staff',
    description: 'Super Admin'
  },
  financeAdmin: {
    employeeId: process.env.TEST_FINANCE_USERNAME || 'MR10001',
    password: process.env.TEST_FINANCE_PASSWORD || 'Test@123',
    loginType: 'staff',
    description: 'Finance Admin'
  },
  admin: {
    employeeId: process.env.TEST_ADMIN_USERNAME || 'MR10001',
    password: process.env.TEST_ADMIN_PASSWORD || 'Test@123',
    loginType: 'staff',
    description: 'Admin User'
  },
  user: {
    mnrId: process.env.TEST_USER_MNR_ID || 'MNRPW005',
    password: process.env.TEST_USER_PASSWORD || TEST_PASSWORD,
    loginType: 'user',
    description: 'Regular MNR User'
  },
  partner: {
    mnrId: process.env.TEST_PARTNER_MNR_ID || 'MNRPW005',
    password: process.env.TEST_PARTNER_PASSWORD || TEST_PASSWORD,
    loginType: 'user',
    description: 'Partner User'
  }
};

const ROLE_PAGE_MAPPING = {
  staff: ['STAFF_PAGES'],
  rvz: ['RVZ_PAGES', 'ADMIN_PAGES'],
  superAdmin: ['RVZ_PAGES', 'ADMIN_PAGES'],
  financeAdmin: ['ADMIN_PAGES'],
  admin: ['ADMIN_PAGES'],
  user: ['USER_PAGES'],
  partner: ['PARTNER_PAGES', 'USER_PAGES']
};

function validateCredentials(role) {
  const creds = TEST_CREDENTIALS[role];
  if (!creds) {
    throw new Error(`Unknown role: ${role}. Available roles: ${Object.keys(TEST_CREDENTIALS).join(', ')}`);
  }
  
  const requiredFields = creds.loginType === 'staff' ? ['employeeId', 'password'] : ['mnrId', 'password'];
  const hasCredentials = requiredFields.every(field => creds[field] && creds[field].length > 0);
  
  if (!hasCredentials) {
    console.warn(`Warning: Missing credentials for ${role} role (${creds.description}). Set environment variables.`);
  }
  return hasCredentials;
}

function getCredentials(role) {
  if (!validateCredentials(role)) {
    console.log(`Required environment variables for ${role}:`);
    const envVars = {
      staff: ['TEST_STAFF_EMPLOYEE_ID', 'TEST_STAFF_PASSWORD'],
      rvz: ['TEST_RVZ_USERNAME', 'TEST_RVZ_PASSWORD'],
      superAdmin: ['TEST_SUPERADMIN_USERNAME', 'TEST_SUPERADMIN_PASSWORD'],
      financeAdmin: ['TEST_FINANCE_USERNAME', 'TEST_FINANCE_PASSWORD'],
      admin: ['TEST_ADMIN_USERNAME', 'TEST_ADMIN_PASSWORD'],
      user: ['TEST_USER_MNR_ID', 'TEST_USER_PASSWORD'],
      partner: ['TEST_PARTNER_MNR_ID', 'TEST_PARTNER_PASSWORD']
    };
    console.log(envVars[role]?.join(', '));
  }
  return TEST_CREDENTIALS[role];
}

function getLoginType(role) {
  const creds = TEST_CREDENTIALS[role];
  return creds ? creds.loginType : 'staff';
}

function getAllRoles() {
  return Object.keys(TEST_CREDENTIALS);
}

function getRoleDescription(role) {
  const creds = TEST_CREDENTIALS[role];
  return creds ? creds.description : 'Unknown Role';
}

function getPagesForRole(role) {
  return ROLE_PAGE_MAPPING[role] || [];
}

module.exports = {
  TEST_CREDENTIALS,
  ROLE_PAGE_MAPPING,
  validateCredentials,
  getCredentials,
  getLoginType,
  getAllRoles,
  getRoleDescription,
  getPagesForRole
};
