"use client";

import Link from "next/link";

export default function PortalSelectionPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans selection:bg-brand-warning/30 selection:text-brand-warning">
      <div className="sm:mx-auto sm:w-full sm:max-w-3xl text-center">
        <div className="mx-auto w-16 h-16 bg-brand-warning rounded-2xl text-white flex items-center justify-center font-bold shadow-lg mb-6 shadow-brand-warning/20">
          <span className="text-2xl">M</span>
        </div>
        <h2 className="text-4xl font-extrabold text-gray-900 tracking-tight mb-3">
          Select Your Portal
        </h2>
        <p className="text-lg text-gray-500 max-w-xl mx-auto">
          Welcome to the MyntReal Enterprise Hub. Please choose the portal that matches your account type to continue.
        </p>
      </div>

      <div className="mt-12 sm:mx-auto sm:w-full sm:max-w-5xl px-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          
          {/* Staff Portal */}
          <Link href="/login" className="group">
            <div className="h-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gray-50 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>
              <div className="relative z-10">
                <div className="w-14 h-14 bg-gray-900 text-white rounded-xl flex items-center justify-center text-2xl mb-6 shadow-sm">
                  <i className="fas fa-id-badge"></i>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Staff Portal</h3>
                <p className="text-sm text-gray-500 leading-relaxed">
                  For internal MyntReal employees, HR, management, and administrative operations.
                </p>
              </div>
            </div>
          </Link>

          {/* VGK Portal */}
          <Link href="/vgk-login" className="group">
            <div className="h-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>
              <div className="relative z-10">
                <div className="w-14 h-14 bg-gradient-to-br from-amber-500 to-orange-600 text-white rounded-xl flex items-center justify-center text-2xl mb-6 shadow-sm">
                  <i className="fas fa-crown"></i>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">VGK Platform</h3>
                <p className="text-sm text-gray-500 leading-relaxed">
                  For VGK4U Supreme and authorized partners managing downline hierarchies.
                </p>
              </div>
            </div>
          </Link>

          {/* Member Portal */}
          <Link href="/member-login" className="group">
            <div className="h-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>
              <div className="relative z-10">
                <div className="w-14 h-14 bg-blue-600 text-white rounded-xl flex items-center justify-center text-2xl mb-6 shadow-sm">
                  <i className="fas fa-users"></i>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">For You Member</h3>
                <p className="text-sm text-gray-500 leading-relaxed">
                  For registered field members managing independent sales and downlines.
                </p>
              </div>
            </div>
          </Link>

          {/* Customer Portal */}
          <Link href="/customer-login" className="group">
            <div className="h-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-50 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-110"></div>
              <div className="relative z-10">
                <div className="w-14 h-14 bg-emerald-600 text-white rounded-xl flex items-center justify-center text-2xl mb-6 shadow-sm">
                  <i className="fas fa-house-user"></i>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Client Access</h3>
                <p className="text-sm text-gray-500 leading-relaxed">
                  For property buyers and investors to track payments and project progress.
                </p>
              </div>
            </div>
          </Link>

        </div>
      </div>
      
      <div className="mt-16 text-center">
        <Link href="/" className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
          <i className="fas fa-arrow-left mr-2"></i> Return to Main Website
        </Link>
      </div>
    </div>
  );
}
