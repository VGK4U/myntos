"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function VendorReturnsPage() {
  return (
    <GenericDataTable 
      title="Vendor Returns"
      endpoint="/staff/inventory/vendor-returns"
      subtitle="Auto-mapped data viewer for staff/inventory/vendor-returns"
    />
  );
}
