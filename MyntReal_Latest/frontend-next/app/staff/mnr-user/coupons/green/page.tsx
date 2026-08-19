"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function GreenPage() {
  return (
    <GenericDataTable 
      title="Green"
      endpoint="/staff/mnr-user/coupons/green"
      subtitle="Auto-mapped data viewer for staff/mnr-user/coupons/green"
    />
  );
}
