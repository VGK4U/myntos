"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ConsultantInvoicesPage() {
  return (
    <GenericDataTable 
      title="Consultant Invoices"
      endpoint="/staff/payroll/consultant-invoices"
      subtitle="Auto-mapped data viewer for staff/payroll/consultant-invoices"
    />
  );
}
