"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BannerAnalyticsPage() {
  return (
    <GenericDataTable 
      title="Banner Analytics"
      endpoint="/staff/mnr/banner-analytics"
      subtitle="Auto-mapped data viewer for staff/mnr/banner-analytics"
    />
  );
}
