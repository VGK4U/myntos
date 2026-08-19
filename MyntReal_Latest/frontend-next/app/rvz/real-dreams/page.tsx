"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RealDreamsPage() {
  return (
    <GenericDataTable 
      title="Real Dreams"
      endpoint="/rvz/real-dreams"
      subtitle="Auto-mapped data viewer for rvz/real-dreams"
    />
  );
}
