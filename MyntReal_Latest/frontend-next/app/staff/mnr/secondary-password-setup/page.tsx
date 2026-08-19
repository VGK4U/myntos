"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SecondaryPasswordSetupPage() {
  return (
    <GenericDataTable 
      title="Secondary Password Setup"
      endpoint="/staff/mnr/secondary-password-setup"
      subtitle="Auto-mapped data viewer for staff/mnr/secondary-password-setup"
    />
  );
}
