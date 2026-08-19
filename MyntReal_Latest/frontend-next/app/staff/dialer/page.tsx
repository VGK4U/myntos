"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DialerPage() {
  return (
    <GenericDataTable 
      title="Dialer"
      endpoint="/staff/dialer"
      subtitle="Auto-mapped data viewer for staff/dialer"
    />
  );
}
