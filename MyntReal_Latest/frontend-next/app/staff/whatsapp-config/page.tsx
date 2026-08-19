"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function WhatsappConfigPage() {
  return (
    <GenericDataTable 
      title="Whatsapp Config"
      endpoint="/staff/whatsapp-config"
      subtitle="Auto-mapped data viewer for staff/whatsapp-config"
    />
  );
}
