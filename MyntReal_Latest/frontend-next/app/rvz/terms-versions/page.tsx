"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsVersionsPage() {
  return (
    <GenericDataTable 
      title="Terms Versions"
      endpoint="/rvz/terms-versions"
      subtitle="Auto-mapped data viewer for rvz/terms-versions"
    />
  );
}
