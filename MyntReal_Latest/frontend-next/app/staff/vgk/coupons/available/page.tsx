"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AvailablePage() {
  return (
    <GenericDataTable 
      title="Available"
      endpoint="/staff/vgk/coupons/available"
      subtitle="Auto-mapped data viewer for staff/vgk/coupons/available"
    />
  );
}
