"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DashboardPage() {
  return (
    <GenericDataTable 
      title="Dashboard"
      endpoint="/staff/mnr-user/segments/vgk4u/dashboard"
      subtitle="Auto-mapped data viewer for staff/mnr-user/segments/vgk4u/dashboard"
    />
  );
}
