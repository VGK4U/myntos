"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PinsPage() {
  return (
    <GenericDataTable 
      title="Pins"
      endpoint="/staff/mnr/pins"
      subtitle="Auto-mapped data viewer for staff/mnr/pins"
    />
  );
}
