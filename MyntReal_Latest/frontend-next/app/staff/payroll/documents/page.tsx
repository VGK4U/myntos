"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DocumentsPage() {
  return (
    <GenericDataTable 
      title="Documents"
      endpoint="/staff/payroll/documents"
      subtitle="Auto-mapped data viewer for staff/payroll/documents"
    />
  );
}
