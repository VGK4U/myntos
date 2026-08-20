"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MyLeavesPage() {
  return (
    <GenericDataTable 
      title="My Leaves"
      endpoint="/staff/my-leaves"
      subtitle="Auto-mapped data viewer for staff/my-leaves"
    />
  );
}
