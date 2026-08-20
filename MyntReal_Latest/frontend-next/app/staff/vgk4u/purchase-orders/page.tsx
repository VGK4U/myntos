"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PurchaseOrdersPage() {
  return (
    <GenericDataTable 
      title="Purchase Orders"
      endpoint="/staff/vgk4u/purchase-orders"
      subtitle="Auto-mapped data viewer for staff/vgk4u/purchase-orders"
    />
  );
}
