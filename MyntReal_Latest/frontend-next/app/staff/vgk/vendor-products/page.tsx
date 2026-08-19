"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function VendorProductsPage() {
  return (
    <GenericDataTable 
      title="Vendor Products"
      endpoint="/staff/vgk/vendor-products"
      subtitle="Auto-mapped data viewer for staff/vgk/vendor-products"
    />
  );
}
