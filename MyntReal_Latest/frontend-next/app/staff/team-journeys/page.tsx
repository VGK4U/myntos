"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TeamJourneysPage() {
  return (
    <GenericDataTable 
      title="Team Journeys"
      endpoint="/staff/team-journeys"
      subtitle="Auto-mapped data viewer for staff/team-journeys"
    />
  );
}
