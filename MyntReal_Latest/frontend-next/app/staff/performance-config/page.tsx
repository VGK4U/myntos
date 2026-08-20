"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PerformanceConfigPage() {
  return (
    <GenericDataTable 
      title="Performance Config"
      endpoint="/staff/performance-config"
      subtitle="Auto-mapped data viewer for staff/performance-config"
    />
  );
}
