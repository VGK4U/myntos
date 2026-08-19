"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MyJourneysPage() {
  return (
    <GenericDataTable 
      title="My Journeys"
      endpoint="/staff/my-journeys"
      subtitle="Auto-mapped data viewer for staff/my-journeys"
    />
  );
}
