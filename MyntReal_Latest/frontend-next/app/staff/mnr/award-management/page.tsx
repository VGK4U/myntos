"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AwardManagementPage() {
  return (
    <GenericDataTable 
      title="Award Management"
      endpoint="/staff/mnr/award-management"
      subtitle="Auto-mapped data viewer for staff/mnr/award-management"
    />
  );
}
