"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MyTenantPage() {
  return (
    <GenericDataTable 
      title="My Tenant"
      endpoint="/staff/my-tenant"
      subtitle="Auto-mapped data viewer for staff/my-tenant"
    />
  );
}
