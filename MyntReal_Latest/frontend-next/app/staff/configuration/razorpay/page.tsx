"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function RazorpayPage() {
  return (
    <GenericDataTable 
      title="Razorpay"
      endpoint="/staff/configuration/razorpay"
      subtitle="Auto-mapped data viewer for staff/configuration/razorpay"
    />
  );
}
