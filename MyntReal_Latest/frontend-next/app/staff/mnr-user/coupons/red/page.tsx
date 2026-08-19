"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RedPage() {
  return (
    <GenericDataTable 
      title="Red"
      endpoint="/staff/mnr-user/coupons/red"
      subtitle="Auto-mapped data viewer for staff/mnr-user/coupons/red"
    />
  );
}
