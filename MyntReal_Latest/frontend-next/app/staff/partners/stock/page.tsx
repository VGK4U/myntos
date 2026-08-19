"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function StockPage() {
  return (
    <GenericDataTable 
      title="Stock"
      endpoint="/staff/partners/stock"
      subtitle="Auto-mapped data viewer for staff/partners/stock"
    />
  );
}
