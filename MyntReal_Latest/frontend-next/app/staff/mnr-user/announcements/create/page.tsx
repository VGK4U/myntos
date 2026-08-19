"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function CreatePage() {
  return (
    <GenericDataTable 
      title="Create"
      endpoint="/staff/mnr-user/announcements/create"
      subtitle="Auto-mapped data viewer for staff/mnr-user/announcements/create"
    />
  );
}
