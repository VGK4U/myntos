"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BirthdaysPage() {
  return (
    <GenericDataTable 
      title="Birthdays"
      endpoint="/staff/mnr/birthdays"
      subtitle="Auto-mapped data viewer for staff/mnr/birthdays"
    />
  );
}
