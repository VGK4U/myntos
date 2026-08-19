"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function WithdrawalSupremePage() {
  return (
    <GenericDataTable 
      title="Withdrawal Supreme"
      endpoint="/staff/mnr/withdrawal-supreme"
      subtitle="Auto-mapped data viewer for staff/mnr/withdrawal-supreme"
    />
  );
}
