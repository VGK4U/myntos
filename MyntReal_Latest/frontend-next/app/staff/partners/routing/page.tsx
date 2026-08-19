"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RoutingPage() {
  return (
    <GenericDataTable 
      title="Routing"
      endpoint="/staff/partners/routing"
      subtitle="Auto-mapped data viewer for staff/partners/routing"
    />
  );
}
