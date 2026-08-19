"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PasswordChangePage() {
  return (
    <GenericDataTable 
      title="Password Change"
      endpoint="/staff/mnr/password-change"
      subtitle="Auto-mapped data viewer for staff/mnr/password-change"
    />
  );
}
