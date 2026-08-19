"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TeamActivitiesPage() {
  return (
    <GenericDataTable 
      title="Team Activities"
      endpoint="/staff/tasks/team-activities"
      subtitle="Auto-mapped data viewer for staff/tasks/team-activities"
    />
  );
}
