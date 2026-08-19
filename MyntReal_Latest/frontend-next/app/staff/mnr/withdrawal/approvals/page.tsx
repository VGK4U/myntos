"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ApprovalsPage() {
  return (
    <GenericDataTable 
      title="Approvals"
      endpoint="/staff/mnr/withdrawal/approvals"
      subtitle="Auto-mapped data viewer for staff/mnr/withdrawal/approvals"
    />
  );
}
