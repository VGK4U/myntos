"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function StockItemsPage() {
  return (
    <GenericDataTable 
      title="Stock Items"
      endpoint="/staff/inventory/stock-items"
      subtitle="Auto-mapped data viewer for staff/inventory/stock-items"
    />
  );
}
