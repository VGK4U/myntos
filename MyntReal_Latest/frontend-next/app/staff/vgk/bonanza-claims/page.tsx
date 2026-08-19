"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BonanzaClaimsPage() {
  return (
    <GenericDataTable 
      title="Bonanza Claims"
      endpoint="/staff/vgk/bonanza-claims"
      subtitle="Auto-mapped data viewer for staff/vgk/bonanza-claims"
    />
  );
}
