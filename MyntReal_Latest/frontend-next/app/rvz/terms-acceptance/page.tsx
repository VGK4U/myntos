"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsAcceptancePage() {
  return (
    <GenericDataTable 
      title="Terms Acceptance"
      endpoint="/rvz/terms-acceptance"
      subtitle="Auto-mapped data viewer for rvz/terms-acceptance"
    />
  );
}
