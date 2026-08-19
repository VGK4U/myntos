"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ExpenseOverviewPage() {
  return (
    <GenericDataTable 
      title="Expense Overview"
      endpoint="/staff/mnr/expense-overview"
      subtitle="Auto-mapped data viewer for staff/mnr/expense-overview"
    />
  );
}
