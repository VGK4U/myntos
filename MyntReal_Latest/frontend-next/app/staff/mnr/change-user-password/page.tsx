"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ChangeUserPasswordPage() {
  return (
    <GenericDataTable 
      title="Change User Password"
      endpoint="/staff/mnr/change-user-password"
      subtitle="Auto-mapped data viewer for staff/mnr/change-user-password"
    />
  );
}
