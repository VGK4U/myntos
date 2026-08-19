"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ExpenseDetailsPage() {
  return (
    <GenericDataTable 
      title="Expense Details"
      endpoint="/staff/mnr/expense-details"
      subtitle="Auto-mapped data viewer for staff/mnr/expense-details"
    />
  );
}
