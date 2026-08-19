"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CodesSegmentsPage() {
  return (
    <GenericDataTable 
      title="Codes Segments"
      endpoint="/staff/marketplace/codes-segments"
      subtitle="Auto-mapped data viewer for staff/marketplace/codes-segments"
    />
  );
}
