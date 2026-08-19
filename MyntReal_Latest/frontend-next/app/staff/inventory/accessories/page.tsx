"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AccessoriesPage() {
  return (
    <GenericDataTable 
      title="Accessories"
      endpoint="/staff/inventory/accessories"
      subtitle="Auto-mapped data viewer for staff/inventory/accessories"
    />
  );
}
