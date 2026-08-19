"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TaskReviewPage() {
  return (
    <GenericDataTable 
      title="Task Review"
      endpoint="/staff/task-review"
      subtitle="Auto-mapped data viewer for staff/task-review"
    />
  );
}
