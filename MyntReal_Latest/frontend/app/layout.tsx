import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Mynt OS — Enterprise Management Platform',
  description: 'Multi-Tenant Master OS for MNR, VGK4U, ZY Real Estate, Accounts, and Team Operations',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
      </head>
      <body className="bg-bg-dark text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
