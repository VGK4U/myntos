"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function UserActivationControlPage() {
  return (
    <GenericDataTable 
      title="User Activation Control"
      endpoint="/staff/mnr/user-activation-control"
      subtitle="Auto-mapped data viewer for staff/mnr/user-activation-control"
    />
  );
}
