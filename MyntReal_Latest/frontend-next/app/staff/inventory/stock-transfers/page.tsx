"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function StockTransfersPage() {
  return (
    <GenericDataTable 
      title="Stock Transfers"
      endpoint="/staff/inventory/stock-transfers"
      subtitle="Auto-mapped data viewer for staff/inventory/stock-transfers"
    />
  );
}
