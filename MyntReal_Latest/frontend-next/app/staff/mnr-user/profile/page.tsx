"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import MemberSearchHeader from '@/components/shared/MemberSearchHeader';
import DataSection from '@/components/shared/DataSection';

interface ProfileData {
  mnr_id: string;
  data: {
    personal: any;
    referral: any;
    address: any;
    bank: any;
  };
}

function ProfileContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { staffFetch } = useStaffFetch();
  
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<ProfileData | null>(null);

  useEffect(() => {
    const mnrParam = searchParams.get('mnr_id');
    if (mnrParam && !profileData && !isSearching) {
      handleSearch(mnrParam);
    }
  }, [searchParams]);

  const handleSearch = async (mnrId: string) => {
    let cleanMnrId = mnrId.trim().toUpperCase();
    if (!cleanMnrId.startsWith('MNR')) cleanMnrId = 'MNR' + cleanMnrId;

    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set('mnr_id', cleanMnrId);
    router.push(`${pathname}?${newParams.toString()}`);

    setIsSearching(true);
    setError(null);
    setProfileData(null);

    try {
      const response = await staffFetch(`/api/v1/staff/mnr-user/profile/${cleanMnrId}`);
      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || 'Member profile not found');
      }
      const data = await response.json();
      setProfileData(data);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-12">
      <MemberSearchHeader 
        title="Member Profile"
        subtitle="View complete member profile details"
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        }
        onSearch={handleSearch}
        isSearching={isSearching}
        memberInfo={profileData ? {
          name: profileData.data.personal?.name,
          id: profileData.mnr_id,
        } : null}
      />

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6 flex items-center gap-3">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>{error}</p>
        </div>
      )}

      {profileData && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DataSection 
              title="Personal Information"
              icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              fields={[
                { label: 'Full Name', value: profileData.data.personal?.name },
                { label: 'MNR ID', value: profileData.mnr_id },
                { label: 'Mobile', value: profileData.data.personal?.mobile },
                { label: 'Email', value: profileData.data.personal?.email },
                { label: 'Date of Birth', value: profileData.data.personal?.date_of_birth },
                { label: 'Gender', value: profileData.data.personal?.gender },
              ]}
            />
            <DataSection 
              title="Referral Information"
              icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>}
              fields={[
                { label: 'Referrer ID', value: profileData.data.referral?.referrer_id },
                { label: 'Referrer Name', value: profileData.data.referral?.referrer_name },
                { label: 'Placement Side', value: profileData.data.referral?.placement_side },
                { label: 'Join Date', value: profileData.data.referral?.join_date },
                { label: 'Package', value: profileData.data.referral?.package_name },
                { label: 'Status', value: profileData.data.referral?.status },
              ]}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DataSection 
              title="Address"
              icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
              fields={[
                { label: 'Address', value: profileData.data.address?.address },
                { label: 'City', value: profileData.data.address?.city },
                { label: 'State', value: profileData.data.address?.state },
                { label: 'Pincode', value: profileData.data.address?.pincode },
              ]}
            />
            <DataSection 
              title="Bank Details"
              icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>}
              fields={[
                { label: 'Bank Name', value: profileData.data.bank?.bank_name },
                { label: 'Account No', value: profileData.data.bank?.account_masked, isMasked: true },
                { label: 'IFSC Code', value: profileData.data.bank?.ifsc },
                { label: 'KYC Status', value: profileData.data.bank?.kyc_status },
              ]}
            />
          </div>
        </div>
      )}

      {!profileData && !error && !isSearching && (
        <div className="text-center py-16 px-4">
          <div className="w-16 h-16 mx-auto bg-gray-50 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 21h7a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v11m0 5l4.879-4.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-600">No Member Selected</h3>
          <p className="text-gray-400 mt-2">Enter an MNR ID above to view their profile</p>
        </div>
      )}
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading Profile...</div>}>
      <ProfileContent />
    </Suspense>
  );
}
