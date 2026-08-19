"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AttendanceExceptionsPage() {
  return (
    <GenericDataTable 
      title="Attendance Exceptions"
      endpoint="/staff/attendance-exceptions"
      subtitle="Auto-mapped data viewer for staff/attendance-exceptions"
    />
  );
}
