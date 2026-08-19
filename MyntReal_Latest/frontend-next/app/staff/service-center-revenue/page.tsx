"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ServiceCenterRevenuePage() {
  return (
    <GenericDataTable 
      title="Service Center Revenue"
      endpoint="/staff/service-center-revenue"
      subtitle="Auto-mapped data viewer for staff/service-center-revenue"
    />
  );
}
