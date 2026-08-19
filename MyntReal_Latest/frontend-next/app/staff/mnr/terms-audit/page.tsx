"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsAuditPage() {
  return (
    <GenericDataTable 
      title="Terms Audit"
      endpoint="/staff/mnr/terms-audit"
      subtitle="Auto-mapped data viewer for staff/mnr/terms-audit"
    />
  );
}
