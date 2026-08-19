"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CenterPage() {
  return (
    <GenericDataTable 
      title="Center"
      endpoint="/staff/meta-ads/center"
      subtitle="Auto-mapped data viewer for staff/meta-ads/center"
    />
  );
}
