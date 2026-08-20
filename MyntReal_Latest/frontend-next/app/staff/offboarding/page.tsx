"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function OffboardingPage() {
  return (
    <GenericDataTable 
      title="Offboarding"
      endpoint="/staff/offboarding"
      subtitle="Auto-mapped data viewer for staff/offboarding"
    />
  );
}
