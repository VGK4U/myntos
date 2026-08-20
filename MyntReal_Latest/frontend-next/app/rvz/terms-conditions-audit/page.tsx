"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsConditionsAuditPage() {
  return (
    <GenericDataTable 
      title="Terms Conditions Audit"
      endpoint="/rvz/terms-conditions-audit"
      subtitle="Auto-mapped data viewer for rvz/terms-conditions-audit"
    />
  );
}
