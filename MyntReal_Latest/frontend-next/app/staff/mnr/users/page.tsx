"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function UsersPage() {
  return (
    <GenericDataTable 
      title="Users"
      endpoint="/staff/mnr/users"
      subtitle="Auto-mapped data viewer for staff/mnr/users"
    />
  );
}
