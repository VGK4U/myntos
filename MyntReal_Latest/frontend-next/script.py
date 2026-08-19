import os

base_dir = r"C:\Desktop\VGK4U\MyntReal_Latest\frontend-next\app\staff\vgk"

pages = {
    "bonanza-claims": ("Bonanza Claims", "Manage and process bonanza claims efficiently.", "Trophy", ["Claim ID", "User", "Amount", "Status", "Date"]),
    "bonanza-management": ("Bonanza Management", "Create and manage bonanza programs.", "Gift", ["Bonanza ID", "Name", "Start Date", "End Date", "Status"]),
    "cash-income/accounts": ("Cash Income Accounts", "Monitor cash income accounts.", "Wallet", ["Account ID", "User", "Balance", "Last Updated", "Status"]),
    "cash-income/sales": ("Cash Income Sales", "Track cash income from sales.", "TrendingUp", ["Sale ID", "Product", "Amount", "Date", "Status"]),
    "config": ("System Configuration", "Manage VGK system settings.", "Settings", ["Config Key", "Value", "Description", "Last Updated", "Action"]),
    "coupons/available": ("Available Coupons", "Manage available discount coupons.", "Ticket", ["Coupon Code", "Discount", "Expiry Date", "Usage Limit", "Status"]),
    "gallery": ("Media Gallery", "View and manage media gallery items.", "Image", ["Image ID", "Title", "Uploaded By", "Date", "Visibility"]),
    "income": ("Income Tracking", "Track overall income sources.", "DollarSign", ["Transaction ID", "Source", "Amount", "Date", "Status"]),
    "income-unified": ("Unified Income", "Unified view of all income streams.", "PieChart", ["Stream ID", "Category", "Total", "Period", "Status"]),
    "media": ("Media Library", "Manage all uploaded media assets.", "Film", ["Media ID", "Type", "Size", "Uploaded At", "Action"]),
    "members": ("Members", "Manage and view all registered members.", "Users", ["Member ID", "Name", "Email", "Joined Date", "Status"]),
    "partner-kyc-review": ("Partner KYC Review", "Review and verify partner KYC documents.", "FileText", ["KYC ID", "Partner Name", "Document Type", "Submitted On", "Status"])
}

template = """\"use client\";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { %s as Icon, Search, Plus, MoreHorizontal } from 'lucide-react';

export default function %sPage() {
  const [searchTerm, setSearchTerm] = useState('');

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Icon className="h-8 w-8 text-primary" />
            %s
          </h1>
          <p className="text-muted-foreground mt-1">
            %s
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">Export CSV</Button>
          <Button size="sm" className="gap-1"><Plus className="h-4 w-4"/> Create New</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Records</CardTitle>
            <Icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,234</div>
            <p className="text-xs text-muted-foreground">+20%% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Status</CardTitle>
            <Icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">98%%</div>
            <p className="text-xs text-muted-foreground">Normal operating level</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
            <Icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">42</div>
            <p className="text-xs text-muted-foreground">Actions in last 24h</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Data Overview</CardTitle>
              <CardDescription>Manage and view detailed records.</CardDescription>
            </div>
            <div className="relative w-64">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search records..."
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  %s
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[1, 2, 3, 4, 5].map((item) => (
                  <TableRow key={item}>
                    <TableCell className="font-medium">#ID-00{item}</TableCell>
                    <TableCell>Sample Data {item}</TableCell>
                    <TableCell>Value {item}</TableCell>
                    <TableCell>2023-10-0{item}</TableCell>
                    <TableCell><Badge variant={item %% 2 === 0 ? "default" : "secondary"}>Active</Badge></TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
"""

for path, info in pages.items():
    title, subtitle, icon, headers = info
    component_name = ''.join(word.capitalize() for word in title.split())
    
    headers_html = '\\n                  '.join(f'<TableHead>{h}</TableHead>' for h in headers)
    
    content = template % (
        icon,
        component_name,
        title,
        subtitle,
        headers_html
    )
    
    full_dir = os.path.join(base_dir, path)
    os.makedirs(full_dir, exist_ok=True)
    file_path = os.path.join(full_dir, 'page.tsx')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Successfully updated 12 pages.')
