import React from 'react';

interface WalletData {
  earning_wallet: number;
  withdrawable_wallet: number;
  upgrade_wallet: number;
  total_withdrawn: number;
}

export default function WalletSummary({ data }: { data: WalletData }) {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="bg-card-start border border-slate-700/50 rounded-lg shadow-sm overflow-hidden h-full">
      <div className="px-6 py-4 border-b border-slate-700/50">
        <h3 className="text-lg font-medium text-white">Wallet Summary</h3>
      </div>
      <div className="p-0">
        <table className="w-full text-sm text-left">
          <tbody className="divide-y divide-slate-700/30">
            <tr className="hover:bg-slate-800/30 transition-colors">
              <td className="px-6 py-4 font-medium text-slate-300">Earning Wallet</td>
              <td className="px-6 py-4 text-right font-semibold text-green-400">
                {formatCurrency(data.earning_wallet)}
              </td>
            </tr>
            <tr className="hover:bg-slate-800/30 transition-colors">
              <td className="px-6 py-4 font-medium text-slate-300">Withdrawable Wallet</td>
              <td className="px-6 py-4 text-right font-semibold text-blue-400">
                {formatCurrency(data.withdrawable_wallet)}
              </td>
            </tr>
            <tr className="hover:bg-slate-800/30 transition-colors">
              <td className="px-6 py-4 font-medium text-slate-300">Upgrade Wallet</td>
              <td className="px-6 py-4 text-right font-semibold text-brand-warning">
                {formatCurrency(data.upgrade_wallet)}
              </td>
            </tr>
            <tr className="hover:bg-slate-800/30 transition-colors">
              <td className="px-6 py-4 font-medium text-slate-400">Total Withdrawn</td>
              <td className="px-6 py-4 text-right font-medium text-slate-400">
                {formatCurrency(data.total_withdrawn)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
