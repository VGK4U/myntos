"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RealDreamsDashboardPage() {
  return (
    <GenericDataTable 
      title="Real Dreams Dashboard"
      endpoint="/rvz/real-dreams-dashboard"
      subtitle="Auto-mapped data viewer for rvz/real-dreams-dashboard"
    />
  );
}
