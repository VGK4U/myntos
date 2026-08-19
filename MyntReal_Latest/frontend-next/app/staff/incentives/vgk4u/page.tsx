"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function Vgk4uPage() {
  return (
    <GenericDataTable 
      title="Vgk4u"
      endpoint="/staff/incentives/vgk4u"
      subtitle="Auto-mapped data viewer for staff/incentives/vgk4u"
    />
  );
}
