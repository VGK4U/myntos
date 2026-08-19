"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RateConfigurationPage() {
  return (
    <GenericDataTable 
      title="Rate Configuration"
      endpoint="/staff/mnr/rate-configuration"
      subtitle="Auto-mapped data viewer for staff/mnr/rate-configuration"
    />
  );
}
