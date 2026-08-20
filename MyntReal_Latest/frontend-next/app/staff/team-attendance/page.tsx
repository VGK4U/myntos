"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TeamAttendancePage() {
  return (
    <GenericDataTable 
      title="Team Attendance"
      endpoint="/staff/team-attendance"
      subtitle="Auto-mapped data viewer for staff/team-attendance"
    />
  );
}
