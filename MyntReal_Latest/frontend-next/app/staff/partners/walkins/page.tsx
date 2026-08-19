"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function WalkinsPage() {
  return (
    <GenericDataTable 
      title="Walkins"
      endpoint="/staff/partners/walkins"
      subtitle="Auto-mapped data viewer for staff/partners/walkins"
    />
  );
}
