"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DailyCeilingPage() {
  return (
    <GenericDataTable 
      title="Daily Ceiling"
      endpoint="/staff/mnr/daily-ceiling"
      subtitle="Auto-mapped data viewer for staff/mnr/daily-ceiling"
    />
  );
}
