"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PageRegistryPage() {
  return (
    <GenericDataTable 
      title="Page Registry"
      endpoint="/staff/page-registry"
      subtitle="Auto-mapped data viewer for staff/page-registry"
    />
  );
}
