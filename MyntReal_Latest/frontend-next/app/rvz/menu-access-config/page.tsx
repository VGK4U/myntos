"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MenuAccessConfigPage() {
  return (
    <GenericDataTable 
      title="Menu Access Config"
      endpoint="/rvz/menu-access-config"
      subtitle="Auto-mapped data viewer for rvz/menu-access-config"
    />
  );
}
