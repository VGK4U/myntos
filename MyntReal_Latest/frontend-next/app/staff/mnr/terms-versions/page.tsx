"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsVersionsPage() {
  return (
    <GenericDataTable 
      title="Terms Versions"
      endpoint="/staff/mnr/terms-versions"
      subtitle="Auto-mapped data viewer for staff/mnr/terms-versions"
    />
  );
}
