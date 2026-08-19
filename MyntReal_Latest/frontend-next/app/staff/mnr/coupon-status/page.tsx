"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CouponStatusPage() {
  return (
    <GenericDataTable 
      title="Coupon Status"
      endpoint="/staff/mnr/coupon-status"
      subtitle="Auto-mapped data viewer for staff/mnr/coupon-status"
    />
  );
}
