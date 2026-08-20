"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MarketplacePage() {
  return (
    <GenericDataTable 
      title="Marketplace"
      endpoint="/rvz/real-dreams/marketplace"
      subtitle="Auto-mapped data viewer for rvz/real-dreams/marketplace"
    />
  );
}
