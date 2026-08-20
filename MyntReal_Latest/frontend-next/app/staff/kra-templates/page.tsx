"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function KraTemplatesPage() {
  return (
    <GenericDataTable 
      title="Kra Templates"
      endpoint="/staff/kra-templates"
      subtitle="Auto-mapped data viewer for staff/kra-templates"
    />
  );
}
