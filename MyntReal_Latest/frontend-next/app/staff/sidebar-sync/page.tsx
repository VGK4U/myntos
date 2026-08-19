"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SidebarSyncPage() {
  return (
    <GenericDataTable 
      title="Sidebar Sync"
      endpoint="/staff/sidebar-sync"
      subtitle="Auto-mapped data viewer for staff/sidebar-sync"
    />
  );
}
