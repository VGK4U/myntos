"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CompanyEarningsPage() {
  return (
    <GenericDataTable 
      title="Company Earnings"
      endpoint="/staff/mnr/company-earnings"
      subtitle="Auto-mapped data viewer for staff/mnr/company-earnings"
    />
  );
}
