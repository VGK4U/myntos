"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BonanzaPage() {
  return (
    <GenericDataTable 
      title="Bonanza"
      endpoint="/staff/mnr-user/awards/bonanza"
      subtitle="Auto-mapped data viewer for staff/mnr-user/awards/bonanza"
    />
  );
}
