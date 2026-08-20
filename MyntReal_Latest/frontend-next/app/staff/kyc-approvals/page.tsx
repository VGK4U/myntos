"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function KycApprovalsPage() {
  return (
    <GenericDataTable 
      title="Kyc Approvals"
      endpoint="/staff/kyc-approvals"
      subtitle="Auto-mapped data viewer for staff/kyc-approvals"
    />
  );
}
