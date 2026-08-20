"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CallQualityPage() {
  return (
    <GenericDataTable 
      title="Call Quality"
      endpoint="/staff/call-quality"
      subtitle="Auto-mapped data viewer for staff/call-quality"
    />
  );
}
