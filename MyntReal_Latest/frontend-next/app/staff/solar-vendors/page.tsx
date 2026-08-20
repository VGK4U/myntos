"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SolarVendorsPage() {
  return (
    <GenericDataTable 
      title="Solar Vendors"
      endpoint="/staff/solar-vendors"
      subtitle="Auto-mapped data viewer for staff/solar-vendors"
    />
  );
}
