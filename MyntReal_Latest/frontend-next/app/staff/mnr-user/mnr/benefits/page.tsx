"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BenefitsPage() {
  return (
    <GenericDataTable 
      title="Benefits"
      endpoint="/staff/mnr-user/mnr/benefits"
      subtitle="Auto-mapped data viewer for staff/mnr-user/mnr/benefits"
    />
  );
}
