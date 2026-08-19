"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AllPage() {
  return (
    <GenericDataTable 
      title="All"
      endpoint="/staff/mnr-user/members/all"
      subtitle="Auto-mapped data viewer for staff/mnr-user/members/all"
    />
  );
}
