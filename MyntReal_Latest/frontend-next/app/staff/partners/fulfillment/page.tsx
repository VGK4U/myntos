"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function FulfillmentPage() {
  return (
    <GenericDataTable 
      title="Fulfillment"
      endpoint="/staff/partners/fulfillment"
      subtitle="Auto-mapped data viewer for staff/partners/fulfillment"
    />
  );
}
