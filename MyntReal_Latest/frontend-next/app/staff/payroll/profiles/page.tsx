"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ProfilesPage() {
  return (
    <GenericDataTable 
      title="Profiles"
      endpoint="/staff/payroll/profiles"
      subtitle="Auto-mapped data viewer for staff/payroll/profiles"
    />
  );
}
