"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function VedPage() {
  return (
    <GenericDataTable 
      title="Ved"
      endpoint="/staff/mnr-user/mnr/ved"
      subtitle="Auto-mapped data viewer for staff/mnr-user/mnr/ved"
    />
  );
}
