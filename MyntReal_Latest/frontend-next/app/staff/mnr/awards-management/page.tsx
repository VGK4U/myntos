"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AwardsManagementPage() {
  return (
    <GenericDataTable 
      title="Awards Management"
      endpoint="/staff/mnr/awards-management"
      subtitle="Auto-mapped data viewer for staff/mnr/awards-management"
    />
  );
}
