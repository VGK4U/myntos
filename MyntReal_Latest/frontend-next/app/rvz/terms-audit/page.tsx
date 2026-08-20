"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsAuditPage() {
  return (
    <GenericDataTable 
      title="Terms Audit"
      endpoint="/rvz/terms-audit"
      subtitle="Auto-mapped data viewer for rvz/terms-audit"
    />
  );
}
