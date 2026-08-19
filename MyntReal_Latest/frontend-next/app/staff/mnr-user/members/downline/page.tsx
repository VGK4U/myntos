"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DownlinePage() {
  return (
    <GenericDataTable 
      title="Downline"
      endpoint="/staff/mnr-user/members/downline"
      subtitle="Auto-mapped data viewer for staff/mnr-user/members/downline"
    />
  );
}
