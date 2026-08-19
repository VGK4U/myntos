"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RunsPage() {
  return (
    <GenericDataTable 
      title="Runs"
      endpoint="/staff/payroll/runs"
      subtitle="Auto-mapped data viewer for staff/payroll/runs"
    />
  );
}
