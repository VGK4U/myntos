"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function LeaveApprovalsPage() {
  return (
    <GenericDataTable 
      title="Leave Approvals"
      endpoint="/staff/leave-approvals"
      subtitle="Auto-mapped data viewer for staff/leave-approvals"
    />
  );
}
