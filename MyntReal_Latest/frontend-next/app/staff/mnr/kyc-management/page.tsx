"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function KycManagementPage() {
  return (
    <GenericDataTable 
      title="Kyc Management"
      endpoint="/staff/mnr/kyc-management"
      subtitle="Auto-mapped data viewer for staff/mnr/kyc-management"
    />
  );
}
