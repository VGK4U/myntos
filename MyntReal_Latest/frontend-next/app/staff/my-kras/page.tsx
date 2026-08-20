"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MyKrasPage() {
  return (
    <GenericDataTable 
      title="My Kras"
      endpoint="/staff/my-kras"
      subtitle="Auto-mapped data viewer for staff/my-kras"
    />
  );
}
