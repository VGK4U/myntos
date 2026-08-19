"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MyKycPage() {
  return (
    <GenericDataTable 
      title="My Kyc"
      endpoint="/staff/my-kyc"
      subtitle="Auto-mapped data viewer for staff/my-kyc"
    />
  );
}
