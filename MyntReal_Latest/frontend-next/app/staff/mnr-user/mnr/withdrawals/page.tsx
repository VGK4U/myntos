"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function WithdrawalsPage() {
  return (
    <GenericDataTable 
      title="Withdrawals"
      endpoint="/staff/mnr-user/mnr/withdrawals"
      subtitle="Auto-mapped data viewer for staff/mnr-user/mnr/withdrawals"
    />
  );
}
