"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BannersManagementPage() {
  return (
    <GenericDataTable 
      title="Banners Management"
      endpoint="/staff/mnr/banners-management"
      subtitle="Auto-mapped data viewer for staff/mnr/banners-management"
    />
  );
}
