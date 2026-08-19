"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsConditionsManagementPage() {
  return (
    <GenericDataTable 
      title="Terms Conditions Management"
      endpoint="/rvz/terms-conditions-management"
      subtitle="Auto-mapped data viewer for rvz/terms-conditions-management"
    />
  );
}
