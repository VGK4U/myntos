"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TermsEditorPage() {
  return (
    <GenericDataTable 
      title="Terms Editor"
      endpoint="/rvz/terms-editor"
      subtitle="Auto-mapped data viewer for rvz/terms-editor"
    />
  );
}
