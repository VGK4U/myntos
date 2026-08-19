"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ExecutiveDashboardPage() {
  return (
    <GenericDataTable 
      title="Executive Dashboard"
      endpoint="/staff/executive-dashboard"
      subtitle="Auto-mapped data viewer for staff/executive-dashboard"
    />
  );
}
