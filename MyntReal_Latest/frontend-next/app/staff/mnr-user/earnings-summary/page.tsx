"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function EarningsSummaryPage() {
  return (
    <GenericDataTable 
      title="Earnings Summary"
      endpoint="/staff/mnr-user/earnings-summary"
      subtitle="Auto-mapped data viewer for staff/mnr-user/earnings-summary"
    />
  );
}
