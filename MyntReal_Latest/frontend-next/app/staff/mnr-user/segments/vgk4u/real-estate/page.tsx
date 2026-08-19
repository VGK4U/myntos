"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RealEstatePage() {
  return (
    <GenericDataTable 
      title="Real Estate"
      endpoint="/staff/mnr-user/segments/vgk4u/real-estate"
      subtitle="Auto-mapped data viewer for staff/mnr-user/segments/vgk4u/real-estate"
    />
  );
}
