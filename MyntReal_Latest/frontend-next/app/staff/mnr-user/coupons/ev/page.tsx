"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function EvPage() {
  return (
    <GenericDataTable 
      title="Ev"
      endpoint="/staff/mnr-user/coupons/ev"
      subtitle="Auto-mapped data viewer for staff/mnr-user/coupons/ev"
    />
  );
}
