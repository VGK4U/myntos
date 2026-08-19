"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function EmergencyWalletPage() {
  return (
    <GenericDataTable 
      title="Emergency Wallet"
      endpoint="/staff/mnr/emergency-wallet"
      subtitle="Auto-mapped data viewer for staff/mnr/emergency-wallet"
    />
  );
}
