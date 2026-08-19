"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function IntakePage() {
  return (
    <GenericDataTable 
      title="Intake"
      endpoint="/staff/inventory/intake"
      subtitle="Auto-mapped data viewer for staff/inventory/intake"
    />
  );
}
