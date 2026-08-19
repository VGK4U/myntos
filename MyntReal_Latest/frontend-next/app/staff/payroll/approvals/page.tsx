"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ApprovalsPage() {
  return (
    <GenericDataTable 
      title="Approvals"
      endpoint="/staff/payroll/approvals"
      subtitle="Auto-mapped data viewer for staff/payroll/approvals"
    />
  );
}
