"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function A1topPage() {
  return (
    <GenericDataTable 
      title="A1top"
      endpoint="/staff/configuration/a1top"
      subtitle="Auto-mapped data viewer for staff/configuration/a1top"
    />
  );
}
