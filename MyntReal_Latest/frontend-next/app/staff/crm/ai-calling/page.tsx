"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AiCallingPage() {
  return (
    <GenericDataTable 
      title="Ai Calling"
      endpoint="/staff/crm/ai-calling"
      subtitle="Auto-mapped data viewer for staff/crm/ai-calling"
    />
  );
}
