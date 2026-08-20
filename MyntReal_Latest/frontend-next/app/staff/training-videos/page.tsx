"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TrainingVideosPage() {
  return (
    <GenericDataTable 
      title="Training Videos"
      endpoint="/staff/training-videos"
      subtitle="Auto-mapped data viewer for staff/training-videos"
    />
  );
}
