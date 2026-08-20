"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function OperatorCallsPage() {
  return (
    <GenericDataTable 
      title="Operator Calls"
      endpoint="/staff/operator-calls"
      subtitle="Auto-mapped data viewer for staff/operator-calls"
    />
  );
}
