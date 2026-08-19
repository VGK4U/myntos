"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function GuruPage() {
  return (
    <GenericDataTable 
      title="Guru"
      endpoint="/staff/mnr-user/mnr/guru"
      subtitle="Auto-mapped data viewer for staff/mnr-user/mnr/guru"
    />
  );
}
