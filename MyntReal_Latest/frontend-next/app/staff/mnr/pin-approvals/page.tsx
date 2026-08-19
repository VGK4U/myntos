"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PinApprovalsPage() {
  return (
    <GenericDataTable 
      title="Pin Approvals"
      endpoint="/staff/mnr/pin-approvals"
      subtitle="Auto-mapped data viewer for staff/mnr/pin-approvals"
    />
  );
}
