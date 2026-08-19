"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AttendanceReportsPage() {
  return (
    <GenericDataTable 
      title="Attendance Reports"
      endpoint="/staff/attendance-reports"
      subtitle="Auto-mapped data viewer for staff/attendance-reports"
    />
  );
}
