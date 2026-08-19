"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TrainingPage() {
  return (
    <GenericDataTable 
      title="Training"
      endpoint="/staff/mnr-user/segments/vgk4u/training"
      subtitle="Auto-mapped data viewer for staff/mnr-user/segments/vgk4u/training"
    />
  );
}
