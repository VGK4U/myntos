"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SignupCategoriesPage() {
  return (
    <GenericDataTable 
      title="Signup Categories"
      endpoint="/staff/signup-categories"
      subtitle="Auto-mapped data viewer for staff/signup-categories"
    />
  );
}
