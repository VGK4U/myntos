"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function MembersPage() {
  return (
    <GenericDataTable 
      title="Members"
      endpoint="/staff/mnr-user/members"
      subtitle="Auto-mapped data viewer for staff/mnr-user/members"
    />
  );
}
