"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ManagerReviewPage() {
  return (
    <GenericDataTable 
      title="Manager Review"
      endpoint="/staff/manager-review"
      subtitle="Auto-mapped data viewer for staff/manager-review"
    />
  );
}
