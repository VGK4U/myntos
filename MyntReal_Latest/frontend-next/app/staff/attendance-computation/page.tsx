"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AttendanceComputationPage() {
  return (
    <GenericDataTable 
      title="Attendance Computation"
      endpoint="/staff/attendance-computation"
      subtitle="Auto-mapped data viewer for staff/attendance-computation"
    />
  );
}
