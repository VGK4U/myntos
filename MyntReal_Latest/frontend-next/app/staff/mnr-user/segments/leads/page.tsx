"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function LeadsPage() {
  return (
    <GenericDataTable 
      title="Leads"
      endpoint="/staff/mnr-user/segments/leads"
      subtitle="Auto-mapped data viewer for staff/mnr-user/segments/leads"
    />
  );
}
