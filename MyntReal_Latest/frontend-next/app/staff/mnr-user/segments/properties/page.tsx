"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PropertiesPage() {
  return (
    <GenericDataTable 
      title="Properties"
      endpoint="/staff/mnr-user/segments/properties"
      subtitle="Auto-mapped data viewer for staff/mnr-user/segments/properties"
    />
  );
}
