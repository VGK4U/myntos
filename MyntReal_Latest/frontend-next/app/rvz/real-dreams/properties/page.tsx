"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PropertiesPage() {
  return (
    <GenericDataTable 
      title="Properties"
      endpoint="/rvz/real-dreams/properties"
      subtitle="Auto-mapped data viewer for rvz/real-dreams/properties"
    />
  );
}
