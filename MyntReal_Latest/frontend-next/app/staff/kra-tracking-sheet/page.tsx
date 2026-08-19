"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function KraTrackingSheetPage() {
  return (
    <GenericDataTable 
      title="Kra Tracking Sheet"
      endpoint="/staff/kra-tracking-sheet"
      subtitle="Auto-mapped data viewer for staff/kra-tracking-sheet"
    />
  );
}
