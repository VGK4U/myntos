"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SalesRevenuePage() {
  return (
    <GenericDataTable 
      title="Sales Revenue"
      endpoint="/rvz/sales-revenue"
      subtitle="Auto-mapped data viewer for rvz/sales-revenue"
    />
  );
}
