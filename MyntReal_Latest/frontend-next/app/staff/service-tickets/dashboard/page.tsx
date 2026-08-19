"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DashboardPage() {
  return (
    <GenericDataTable 
      title="Dashboard"
      endpoint="/staff/service-tickets/dashboard"
      subtitle="Auto-mapped data viewer for staff/service-tickets/dashboard"
    />
  );
}
