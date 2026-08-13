"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SignupPage() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSignup = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Simulate registration
    setTimeout(() => {
      localStorage.setItem("staff_token", "dummy.jwt.token");
      router.push("/staff/dashboard");
    }, 1500);
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-gray-50">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="mx-auto h-12 w-12 bg-gray-900 rounded-xl flex items-center justify-center mb-4 shadow-sm">
          <i className="fas fa-user-plus text-white text-xl"></i>
        </div>
        <h2 className="mt-2 text-center text-3xl font-extrabold text-gray-900 tracking-tight">
          Create an account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Join the VGK4U platform today
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md animate-in fade-in slide-in-from-bottom-6 duration-700">
        <div className="bg-white py-8 px-4 shadow-sm border border-gray-200 sm:rounded-2xl sm:px-10">
          <form className="space-y-5" onSubmit={handleSignup}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-1">First Name</label>
                <input type="text" required className="block w-full py-2.5 px-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900 sm:text-sm" placeholder="Anil" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-1">Last Name</label>
                <input type="text" required className="block w-full py-2.5 px-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900 sm:text-sm" placeholder="Kumar" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-900 mb-1">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-envelope text-gray-400"></i>
                </div>
                <input type="email" required className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900 sm:text-sm" placeholder="name@vgk4u.com" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-900 mb-1">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-lock text-gray-400"></i>
                </div>
                <input type="password" required className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900 sm:text-sm" placeholder="Create a strong password" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-900 mb-1">Role / Department</label>
              <select className="block w-full py-2.5 px-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900 sm:text-sm">
                <option>Staff Member</option>
                <option>Manager / Admin</option>
                <option>VGK4U Partner</option>
              </select>
            </div>

            <div className="flex items-start mt-2">
              <div className="flex items-center h-5">
                <input id="terms" type="checkbox" required className="h-4 w-4 text-gray-900 focus:ring-gray-900 border-gray-300 rounded cursor-pointer" />
              </div>
              <div className="ml-2 text-sm">
                <label htmlFor="terms" className="font-medium text-gray-700 cursor-pointer">
                  I agree to the <a href="#" className="text-gray-900 underline">Terms of Service</a> and <a href="#" className="text-gray-900 underline">Privacy Policy</a>.
                </label>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-gray-900 hover:bg-black focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 transition-colors disabled:opacity-70"
              >
                {loading ? (
                  <span className="flex items-center gap-2"><i className="fas fa-spinner fa-spin"></i> Creating account...</span>
                ) : (
                  "Create Account"
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-gray-500">Already have an account? </span>
            <Link href="/login" className="font-bold text-gray-900 hover:text-gray-600 transition-colors">
              Sign in instead
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
