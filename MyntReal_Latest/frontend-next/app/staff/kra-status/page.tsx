"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function KraStatusPage() {
  return (
    <GenericDataTable 
      title="Kra Status"
      endpoint="/staff/kra-status"
      subtitle="Auto-mapped data viewer for staff/kra-status"
    />
  );
}
