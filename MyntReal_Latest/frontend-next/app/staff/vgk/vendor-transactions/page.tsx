"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function VendorTransactionsPage() {
  return (
    <GenericDataTable 
      title="Vendor Transactions"
      endpoint="/staff/vgk/vendor-transactions"
      subtitle="Auto-mapped data viewer for staff/vgk/vendor-transactions"
    />
  );
}
