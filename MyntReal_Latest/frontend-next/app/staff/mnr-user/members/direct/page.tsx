"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DirectPage() {
  return (
    <GenericDataTable 
      title="Direct"
      endpoint="/staff/mnr-user/members/direct"
      subtitle="Auto-mapped data viewer for staff/mnr-user/members/direct"
    />
  );
}
