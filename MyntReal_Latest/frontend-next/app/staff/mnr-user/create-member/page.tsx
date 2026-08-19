"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CreateMemberPage() {
  return (
    <GenericDataTable 
      title="Create Member"
      endpoint="/staff/mnr-user/create-member"
      subtitle="Auto-mapped data viewer for staff/mnr-user/create-member"
    />
  );
}
