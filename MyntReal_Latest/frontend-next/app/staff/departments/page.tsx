"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DepartmentsPage() {
  return (
    <GenericDataTable 
      title="Departments"
      endpoint="/staff/departments"
      subtitle="Auto-mapped data viewer for staff/departments"
    />
  );
}
