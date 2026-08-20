"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function WalletPage() {
  return (
    <GenericDataTable 
      title="Wallet"
      endpoint="/staff/vgk/wallet"
      subtitle="Auto-mapped data viewer for staff/vgk/wallet"
    />
  );
}
