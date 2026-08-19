"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BonanzaManagementPage() {
  return (
    <GenericDataTable 
      title="Bonanza Management"
      endpoint="/staff/vgk/bonanza-management"
      subtitle="Auto-mapped data viewer for staff/vgk/bonanza-management"
    />
  );
}
