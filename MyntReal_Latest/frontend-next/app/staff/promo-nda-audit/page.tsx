"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PromoNdaAuditPage() {
  return (
    <GenericDataTable 
      title="Promo Nda Audit"
      endpoint="/staff/promo-nda-audit"
      subtitle="Auto-mapped data viewer for staff/promo-nda-audit"
    />
  );
}
