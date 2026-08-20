"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TimesheetPage() {
  return (
    <GenericDataTable 
      title="Timesheet"
      endpoint="/staff/timesheet"
      subtitle="Auto-mapped data viewer for staff/timesheet"
    />
  );
}
