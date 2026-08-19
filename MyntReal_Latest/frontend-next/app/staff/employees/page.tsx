"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function EmployeesPage() {
  return (
    <GenericDataTable 
      title="Employees"
      endpoint="/staff/employees"
      subtitle="Auto-mapped data viewer for staff/employees"
    />
  );
}
