"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PaymentsPage() {
  return (
    <GenericDataTable 
      title="Payments"
      endpoint="/staff/partners/payments"
      subtitle="Auto-mapped data viewer for staff/partners/payments"
    />
  );
}
