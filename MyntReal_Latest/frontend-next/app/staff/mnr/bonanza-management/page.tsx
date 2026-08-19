"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BonanzaManagementPage() {
  return (
    <GenericDataTable 
      title="Bonanza Management"
      endpoint="/staff/mnr/bonanza-management"
      subtitle="Auto-mapped data viewer for staff/mnr/bonanza-management"
    />
  );
}
