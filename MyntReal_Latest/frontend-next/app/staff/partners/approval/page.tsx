"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ApprovalPage() {
  return (
    <GenericDataTable 
      title="Approval"
      endpoint="/staff/partners/approval"
      subtitle="Auto-mapped data viewer for staff/partners/approval"
    />
  );
}
