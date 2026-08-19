"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function FinanceSupremePage() {
  return (
    <GenericDataTable 
      title="Finance Supreme"
      endpoint="/staff/mnr/finance-supreme"
      subtitle="Auto-mapped data viewer for staff/mnr/finance-supreme"
    />
  );
}
