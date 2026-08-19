"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ServiceCenterTrackingPage() {
  return (
    <GenericDataTable 
      title="Service Center Tracking"
      endpoint="/staff/inventory/service-center-tracking"
      subtitle="Auto-mapped data viewer for staff/inventory/service-center-tracking"
    />
  );
}
