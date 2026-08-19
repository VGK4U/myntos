"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function IncomeUnifiedPage() {
  return (
    <GenericDataTable 
      title="Income Unified"
      endpoint="/staff/vgk/income-unified"
      subtitle="Auto-mapped data viewer for staff/vgk/income-unified"
    />
  );
}
