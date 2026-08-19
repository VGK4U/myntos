"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AccountsPage() {
  return (
    <GenericDataTable 
      title="Accounts"
      endpoint="/staff/vgk/cash-income/accounts"
      subtitle="Auto-mapped data viewer for staff/vgk/cash-income/accounts"
    />
  );
}
