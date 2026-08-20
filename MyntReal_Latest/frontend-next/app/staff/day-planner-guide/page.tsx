"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DayPlannerGuidePage() {
  return (
    <GenericDataTable 
      title="Day Planner Guide"
      endpoint="/staff/day-planner-guide"
      subtitle="Auto-mapped data viewer for staff/day-planner-guide"
    />
  );
}
