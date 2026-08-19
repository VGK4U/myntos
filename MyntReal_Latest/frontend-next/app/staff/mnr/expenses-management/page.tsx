"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ExpensesManagementPage() {
  return (
    <GenericDataTable 
      title="Expenses Management"
      endpoint="/staff/mnr/expenses-management"
      subtitle="Auto-mapped data viewer for staff/mnr/expenses-management"
    />
  );
}
