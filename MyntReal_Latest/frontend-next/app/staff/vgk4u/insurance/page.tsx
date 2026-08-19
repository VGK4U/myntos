"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function InsurancePage() {
  return (
    <GenericDataTable 
      title="Insurance"
      endpoint="/staff/vgk4u/insurance"
      subtitle="Auto-mapped data viewer for staff/vgk4u/insurance"
    />
  );
}
