"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function NdaVersionsPage() {
  return (
    <GenericDataTable 
      title="Nda Versions"
      endpoint="/staff/nda-versions"
      subtitle="Auto-mapped data viewer for staff/nda-versions"
    />
  );
}
