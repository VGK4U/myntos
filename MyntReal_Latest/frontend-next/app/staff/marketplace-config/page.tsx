"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MarketplaceConfigPage() {
  return (
    <GenericDataTable 
      title="Marketplace Config"
      endpoint="/staff/marketplace-config"
      subtitle="Auto-mapped data viewer for staff/marketplace-config"
    />
  );
}
