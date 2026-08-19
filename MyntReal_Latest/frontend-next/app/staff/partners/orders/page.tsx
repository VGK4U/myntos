"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function OrdersPage() {
  return (
    <GenericDataTable 
      title="Orders"
      endpoint="/staff/partners/orders"
      subtitle="Auto-mapped data viewer for staff/partners/orders"
    />
  );
}
