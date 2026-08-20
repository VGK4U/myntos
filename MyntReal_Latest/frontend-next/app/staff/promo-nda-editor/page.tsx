"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PromoNdaEditorPage() {
  return (
    <GenericDataTable 
      title="Promo Nda Editor"
      endpoint="/staff/promo-nda-editor"
      subtitle="Auto-mapped data viewer for staff/promo-nda-editor"
    />
  );
}
