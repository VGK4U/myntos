"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PartnerKycReviewPage() {
  return (
    <GenericDataTable 
      title="Partner Kyc Review"
      endpoint="/staff/vgk/partner-kyc-review"
      subtitle="Auto-mapped data viewer for staff/vgk/partner-kyc-review"
    />
  );
}
