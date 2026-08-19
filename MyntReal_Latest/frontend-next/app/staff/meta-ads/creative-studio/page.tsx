"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CreativeStudioPage() {
  return (
    <GenericDataTable 
      title="Creative Studio"
      endpoint="/staff/meta-ads/creative-studio"
      subtitle="Auto-mapped data viewer for staff/meta-ads/creative-studio"
    />
  );
}
