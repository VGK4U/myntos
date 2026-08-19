"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SettingsPage() {
  return (
    <GenericDataTable 
      title="Settings"
      endpoint="/staff/settings"
      subtitle="Auto-mapped data viewer for staff/settings"
    />
  );
}
