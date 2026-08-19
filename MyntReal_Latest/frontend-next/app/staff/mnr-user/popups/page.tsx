"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PopupsPage() {
  return (
    <GenericDataTable 
      title="Popups"
      endpoint="/staff/mnr-user/popups"
      subtitle="Auto-mapped data viewer for staff/mnr-user/popups"
    />
  );
}
