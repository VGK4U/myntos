"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function VendorCategoriesPage() {
  return (
    <GenericDataTable 
      title="Vendor Categories"
      endpoint="/staff/vgk/vendor-categories"
      subtitle="Auto-mapped data viewer for staff/vgk/vendor-categories"
    />
  );
}
