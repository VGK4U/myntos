"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RaisePage() {
  return (
    <GenericDataTable 
      title="Raise"
      endpoint="/staff/service-tickets/raise"
      subtitle="Auto-mapped data viewer for staff/service-tickets/raise"
    />
  );
}
