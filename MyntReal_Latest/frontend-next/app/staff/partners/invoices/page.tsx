"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function InvoicesPage() {
  return (
    <GenericDataTable 
      title="Invoices"
      endpoint="/staff/partners/invoices"
      subtitle="Auto-mapped data viewer for staff/partners/invoices"
    />
  );
}
