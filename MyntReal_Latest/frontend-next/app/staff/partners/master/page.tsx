"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MasterPage() {
  return (
    <GenericDataTable 
      title="Master"
      endpoint="/staff/partners/master"
      subtitle="Auto-mapped data viewer for staff/partners/master"
    />
  );
}
