"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ViewPage() {
  return (
    <GenericDataTable 
      title="View"
      endpoint="/staff/mnr/announcements/view"
      subtitle="Auto-mapped data viewer for staff/mnr/announcements/view"
    />
  );
}
