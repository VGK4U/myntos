"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function B2bClientsPage() {
  return (
    <GenericDataTable 
      title="B2b Clients"
      endpoint="/staff/b2b-clients"
      subtitle="Auto-mapped data viewer for staff/b2b-clients"
    />
  );
}
