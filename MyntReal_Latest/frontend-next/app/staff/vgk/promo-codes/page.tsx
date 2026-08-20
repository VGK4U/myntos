"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PromoCodesPage() {
  return (
    <GenericDataTable 
      title="Promo Codes"
      endpoint="/staff/vgk/promo-codes"
      subtitle="Auto-mapped data viewer for staff/vgk/promo-codes"
    />
  );
}
