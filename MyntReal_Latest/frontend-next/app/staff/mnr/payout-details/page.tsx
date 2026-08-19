"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PayoutDetailsPage() {
  return (
    <GenericDataTable 
      title="Payout Details"
      endpoint="/staff/mnr/payout-details"
      subtitle="Auto-mapped data viewer for staff/mnr/payout-details"
    />
  );
}
