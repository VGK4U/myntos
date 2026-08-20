"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AuditLogsPage() {
  return (
    <GenericDataTable 
      title="Audit Logs"
      endpoint="/staff/audit-logs"
      subtitle="Auto-mapped data viewer for staff/audit-logs"
    />
  );
}
