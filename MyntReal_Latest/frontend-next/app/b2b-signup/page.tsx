"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function B2bSignupPage() {
  return (
    <GenericDataTable 
      title="B2b Signup"
      endpoint="/b2b-signup"
      subtitle="Auto-mapped data viewer for b2b-signup"
    />
  );
}
