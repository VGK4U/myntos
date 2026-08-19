"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AttendanceSheetPage() {
  return (
    <GenericDataTable 
      title="Attendance Sheet"
      endpoint="/staff/attendance-sheet"
      subtitle="Auto-mapped data viewer for staff/attendance-sheet"
    />
  );
}
