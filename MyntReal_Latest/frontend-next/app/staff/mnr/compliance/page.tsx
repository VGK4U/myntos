"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CompliancePage() {
  return (
    <GenericDataTable 
      title="Compliance"
      endpoint="/staff/mnr/compliance"
      subtitle="Auto-mapped data viewer for staff/mnr/compliance"
    />
  );
}
