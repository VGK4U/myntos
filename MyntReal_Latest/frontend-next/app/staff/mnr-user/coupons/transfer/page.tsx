"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TransferPage() {
  return (
    <GenericDataTable 
      title="Transfer"
      endpoint="/staff/mnr-user/coupons/transfer"
      subtitle="Auto-mapped data viewer for staff/mnr-user/coupons/transfer"
    />
  );
}
