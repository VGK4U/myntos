"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CyclesPage() {
  return (
    <GenericDataTable 
      title="Cycles"
      endpoint="/staff/payroll/cycles"
      subtitle="Auto-mapped data viewer for staff/payroll/cycles"
    />
  );
}
