"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PricingPage() {
  return (
    <GenericDataTable 
      title="Pricing"
      endpoint="/staff/partners/pricing"
      subtitle="Auto-mapped data viewer for staff/partners/pricing"
    />
  );
}
