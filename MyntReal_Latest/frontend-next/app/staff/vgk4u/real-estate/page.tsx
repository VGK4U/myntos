"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RealEstatePage() {
  return (
    <GenericDataTable 
      title="Real Estate"
      endpoint="/staff/vgk4u/real-estate"
      subtitle="Auto-mapped data viewer for staff/vgk4u/real-estate"
    />
  );
}
