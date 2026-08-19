"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CampaignsPage() {
  return (
    <GenericDataTable 
      title="Campaigns"
      endpoint="/staff/meta-ads/campaigns"
      subtitle="Auto-mapped data viewer for staff/meta-ads/campaigns"
    />
  );
}
