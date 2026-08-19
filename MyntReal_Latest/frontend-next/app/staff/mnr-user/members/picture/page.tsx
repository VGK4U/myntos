"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PicturePage() {
  return (
    <GenericDataTable 
      title="Picture"
      endpoint="/staff/mnr-user/members/picture"
      subtitle="Auto-mapped data viewer for staff/mnr-user/members/picture"
    />
  );
}
