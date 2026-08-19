"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function StockValidationPage() {
  return (
    <GenericDataTable 
      title="Stock Validation"
      endpoint="/staff/inventory/stock-validation"
      subtitle="Auto-mapped data viewer for staff/inventory/stock-validation"
    />
  );
}
