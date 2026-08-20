"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function EmployeeDirectoryPage() {
  return (
    <GenericDataTable 
      title="Employee Directory"
      endpoint="/staff/employee-directory"
      subtitle="Auto-mapped data viewer for staff/employee-directory"
    />
  );
}
