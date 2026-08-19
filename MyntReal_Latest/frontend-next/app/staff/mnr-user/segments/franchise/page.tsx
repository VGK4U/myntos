"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function FranchisePage() {
  return (
    <GenericDataTable 
      title="Franchise"
      endpoint="/staff/mnr-user/segments/franchise"
      subtitle="Auto-mapped data viewer for staff/mnr-user/segments/franchise"
    />
  );
}
