"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CallManagementPage() {
  return (
    <GenericDataTable 
      title="Call Management"
      endpoint="/staff/call-management"
      subtitle="Auto-mapped data viewer for staff/call-management"
    />
  );
}
