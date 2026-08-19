"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PromotersPage() {
  return (
    <GenericDataTable 
      title="Promoters"
      endpoint="/staff/promoters"
      subtitle="Auto-mapped data viewer for staff/promoters"
    />
  );
}
