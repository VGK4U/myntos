"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MatchingPage() {
  return (
    <GenericDataTable 
      title="Matching"
      endpoint="/staff/mnr-user/mnr/matching"
      subtitle="Auto-mapped data viewer for staff/mnr-user/mnr/matching"
    />
  );
}
