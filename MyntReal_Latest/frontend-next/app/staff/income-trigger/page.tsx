"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function IncomeTriggerPage() {
  return (
    <GenericDataTable 
      title="Income Trigger"
      endpoint="/staff/income-trigger"
      subtitle="Auto-mapped data viewer for staff/income-trigger"
    />
  );
}
