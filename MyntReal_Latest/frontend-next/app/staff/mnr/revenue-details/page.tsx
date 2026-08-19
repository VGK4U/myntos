"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RevenueDetailsPage() {
  return (
    <GenericDataTable 
      title="Revenue Details"
      endpoint="/staff/mnr/revenue-details"
      subtitle="Auto-mapped data viewer for staff/mnr/revenue-details"
    />
  );
}
