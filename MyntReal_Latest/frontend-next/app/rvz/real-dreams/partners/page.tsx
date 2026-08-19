"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PartnersPage() {
  return (
    <GenericDataTable 
      title="Partners"
      endpoint="/rvz/real-dreams/partners"
      subtitle="Auto-mapped data viewer for rvz/real-dreams/partners"
    />
  );
}
