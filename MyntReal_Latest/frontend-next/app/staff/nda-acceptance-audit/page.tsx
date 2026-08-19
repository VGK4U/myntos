"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function NdaAcceptanceAuditPage() {
  return (
    <GenericDataTable 
      title="Nda Acceptance Audit"
      endpoint="/staff/nda-acceptance-audit"
      subtitle="Auto-mapped data viewer for staff/nda-acceptance-audit"
    />
  );
}
