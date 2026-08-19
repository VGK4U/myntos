"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MyLeadIncentivesPage() {
  return (
    <GenericDataTable 
      title="My Lead Incentives"
      endpoint="/staff/my-lead-incentives"
      subtitle="Auto-mapped data viewer for staff/my-lead-incentives"
    />
  );
}
