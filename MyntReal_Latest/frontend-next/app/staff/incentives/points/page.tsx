"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PointsPage() {
  return (
    <GenericDataTable 
      title="Points"
      endpoint="/staff/incentives/points"
      subtitle="Auto-mapped data viewer for staff/incentives/points"
    />
  );
}
