import os

FILE_PATH = r"C:\Desktop\VGK4U\MyntReal_Latest\frontend-next\app\staff\employees\page.tsx"
os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

CONTENT = """\"\"\"use client\"\"\";

import React, { useState, useEffect, useMemo } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Users, UserCheck, UserX, UserMinus, Building, Search, Edit, Trash, Key, PauseCircle, PlayCircle, List, Network } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [modulesByCategory, setModulesByCategory] = useState<any>({});
  const [partners, setPartners] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [view, setView] = useState<'list'|'tree'>('list');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [staffTypeFilter, setStaffTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [selectedEmp, setSelectedEmp] = useState<any>(null);
  
  const [formData, setFormData] = useState<any>({
    id: '', salutation: '', firstName: '', lastName: '', email: '', phone: '', staffType: 'MN_STAFF', freelancerAccessMode: 'default', roleId: '', departmentId: '', designation: '', dateOfJoining: '', reportingManagerId: '', address: '', employmentType: 'probation', probationPeriodMonths: 6, probationEndDate: '', confirmationDate: '', probationNotes: '', callTrackingEnabled: false, quarterlyBonusEligible: false, teamTag: '', baseCompanyId: '', linkedPartnerId: '', empCode: ''
  });
  const [selectedCompanies, setSelectedCompanies] = useState<number[]>([]);
  const [selectedDepts, setSelectedDepts] = useState<number[]>([]);
  const [selectedModules, setSelectedModules] = useState<number[]>([]);

  // Current user role tracking (simulated for now, replace with actual logic from context)
  const currentUserRoleCode = 'vgk4u'; // Simulated Supreme Admin
  const currentUserId = 1;

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [empRes, roleRes, deptRes, compRes, modRes, partRes] = await Promise.all([
        api.get('/staff/employees'),
        api.get('/staff/roles'),
        api.get('/staff/departments'),
        api.get('/staff/accounts/companies'),
        api.get('/staff/modules/master').catch(() => ({ data: { by_category: {} } })),
        api.get('/partner/partners?limit=200').catch(() => ({ data: { data: [] } }))
      ]);
      setEmployees(empRes.data.employees || empRes.data || []);
      setRoles(roleRes.data.roles || roleRes.data || []);
      setDepartments(deptRes.data.departments || deptRes.data || []);
      setCompanies(compRes.data.companies || compRes.data || []);
      setModulesByCategory(modRes.data.by_category || {});
      setPartners(partRes.data.data || []);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const filteredEmployees = useMemo(() => {
    return employees.filter(emp => {
      const matchSearch = !search || emp.full_name?.toLowerCase().includes(search.toLowerCase()) || emp.email?.toLowerCase().includes(search.toLowerCase()) || emp.employee_code?.toLowerCase().includes(search.toLowerCase());
      const matchRole = !roleFilter || emp.role_id == roleFilter;
      const matchDept = !deptFilter || emp.department_id == deptFilter;
      const matchStaffType = !staffTypeFilter || emp.staff_type === staffTypeFilter;
      const empStatus = emp.status || (emp.is_active ? 'active' : 'inactive');
      const matchStatus = !statusFilter || empStatus === statusFilter;
      return matchSearch && matchRole && matchDept && matchStaffType && matchStatus;
    });
  }, [employees, search, roleFilter, deptFilter, staffTypeFilter, statusFilter]);

  const kpis = useMemo(() => {
    const total = employees.length;
    const active = employees.filter(e => (e.status || (e.is_active ? 'active' : 'inactive')) === 'active').length;
    const inactive = employees.filter(e => (e.status || (e.is_active ? 'active' : 'inactive')) === 'inactive').length;
    const deact = employees.filter(e => e.status === 'deactivated').length;
    const resigned = employees.filter(e => e.status === 'resigned').length;
    const roots = employees.filter(e => !e.reporting_manager_id).length;
    return { total, active, inactive, deact, resigned, roots };
  }, [employees]);

  const handleSave = async () => {
    try {
      const isEdit = !!formData.id;
      const url = isEdit ? `/staff/employees/${formData.id}` : '/staff/employees';
      const method = isEdit ? 'put' : 'post';
      
      const payload: any = {
        salutation: formData.salutation || null,
        first_name: formData.firstName,
        last_name: formData.lastName,
        full_name: [formData.salutation, formData.firstName, formData.lastName].filter(Boolean).join(' '),
        email: formData.email || null,
        phone: formData.phone || null,
        role_id: parseInt(formData.roleId),
        department_id: formData.departmentId ? parseInt(formData.departmentId) : null,
        designation: formData.designation || null,
        date_of_joining: formData.dateOfJoining || null,
        reporting_manager_id: formData.reportingManagerId ? parseInt(formData.reportingManagerId) : null,
        address: formData.address || null,
        module_ids: selectedModules,
        base_company_id: formData.baseCompanyId ? parseInt(formData.baseCompanyId) : null,
        data_companies: selectedCompanies,
        additional_departments: selectedDepts,
        employment_type: formData.employmentType || 'probation',
        probation_period_months: parseInt(formData.probationPeriodMonths) || 6,
        probation_end_date: formData.probationEndDate || null,
        confirmation_date: formData.confirmationDate || null,
        probation_notes: formData.probationNotes || null,
        call_tracking_enabled: formData.callTrackingEnabled,
        is_quarterly_bonus_eligible: formData.quarterlyBonusEligible,
        team_tag: formData.teamTag || null,
        linked_partner_id: formData.linkedPartnerId ? parseInt(formData.linkedPartnerId) : null,
        freelancer_access_mode: formData.freelancerAccessMode
      };

      if (currentUserRoleCode === 'vgk4u') {
        payload.staff_type = formData.staffType;
        if (isEdit && formData.empCode) payload.emp_code = formData.empCode;
      }

      await api[method](url, payload);
      toast.success(isEdit ? 'Employee updated' : 'Employee added');
      setIsModalOpen(false);
      fetchData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save employee');
    }
  };

  const resetPassword = async (empId: number, isSelf: boolean) => {
    if (!confirm('Are you sure you want to reset the password?')) return;
    try {
      await api.post(`/staff/employees/${empId}/reset-password`);
      toast.success('Password reset successfully');
    } catch {
      toast.error('Failed to reset password');
    }
  };

  const deleteEmployee = async (type: 'hard'|'soft') => {
    try {
      await api.delete(`/staff/employees/${selectedEmp.id}/${type}`);
      toast.success('Employee deleted');
      setIsDeleteModalOpen(false);
      fetchData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete employee');
    }
  };

  const changeStatus = async () => {
    try {
      const newStatus = selectedEmp.status === 'active' ? false : true;
      await api.put(`/staff/employees/${selectedEmp.id}`, { is_active: newStatus });
      toast.success('Status updated');
      setIsStatusModalOpen(false);
      fetchData();
    } catch {
      toast.error('Failed to update status');
    }
  };

  const openEditModal = async (emp: any) => {
    setFormData({
      id: emp.id, salutation: emp.salutation || '', firstName: emp.first_name || '', lastName: emp.last_name || '', email: emp.email || '', phone: emp.phone || '', staffType: emp.staff_type || 'MYNT_REAL', freelancerAccessMode: emp.freelancer_access_mode || 'default', roleId: emp.role_id || '', departmentId: emp.department_id || '', designation: emp.designation || '', dateOfJoining: emp.date_of_joining || '', reportingManagerId: emp.reporting_manager_id || '', address: emp.address || '', employmentType: emp.employment_type || 'probation', probationPeriodMonths: emp.probation_period_months || 6, probationEndDate: emp.probation_end_date || '', confirmationDate: emp.confirmation_date || '', probationNotes: emp.probation_notes || '', callTrackingEnabled: emp.call_tracking_enabled || false, quarterlyBonusEligible: emp.is_quarterly_bonus_eligible || false, teamTag: emp.team_tag || '', baseCompanyId: emp.base_company_id || '', linkedPartnerId: emp.linked_partner_id || '', empCode: emp.emp_code || emp.employee_code || ''
    });
    setSelectedCompanies((emp.data_companies || []).map((c: any) => c.id || c));
    setSelectedDepts((emp.additional_departments || []).map((d: any) => d.id || d));
    
    try {
      const modRes = await api.get(`/staff/employees/${emp.id}/modules`);
      setSelectedModules(modRes.data.module_ids || []);
    } catch {
      setSelectedModules([]);
    }
    
    setIsModalOpen(true);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {[
          { label: 'Total', val: kpis.total, icon: Users, color: 'text-indigo-600', bg: 'bg-indigo-100' },
          { label: 'Active', val: kpis.active, icon: UserCheck, color: 'text-emerald-600', bg: 'bg-emerald-100' },
          { label: 'Inactive', val: kpis.inactive, icon: PauseCircle, color: 'text-amber-600', bg: 'bg-amber-100' },
          { label: 'Deactivated', val: kpis.deact, icon: UserMinus, color: 'text-red-600', bg: 'bg-red-100' },
          { label: 'Resigned', val: kpis.resigned, icon: UserX, color: 'text-gray-600', bg: 'bg-gray-100' },
          { label: 'Departments', val: departments.length, icon: Building, color: 'text-purple-600', bg: 'bg-purple-100' },
          { label: 'Top Managers', val: kpis.roots, icon: Network, color: 'text-sky-600', bg: 'bg-sky-100' }
        ].map((k, i) => (
          <Card key={i} className="flex flex-col items-center justify-center p-4">
            <div className={`p-3 rounded-full ${k.bg} ${k.color} mb-2`}>
              <k.icon className="w-6 h-6" />
            </div>
            <div className="text-2xl font-bold">{k.val}</div>
            <div className="text-xs text-gray-500 uppercase font-semibold">{k.label}</div>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-col md:flex-row items-center justify-between space-y-2 md:space-y-0">
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" /> All Employees
          </CardTitle>
          <div className="flex gap-2">
            <Button variant={view === 'list' ? 'default' : 'outline'} onClick={() => setView('list')}><List className="w-4 h-4 mr-2" /> List</Button>
            <Button variant={view === 'tree' ? 'default' : 'outline'} onClick={() => setView('tree')}><Network className="w-4 h-4 mr-2" /> Tree</Button>
            {currentUserRoleCode === 'vgk4u' && (
              <Button onClick={() => { setFormData({ id: '', staffType: 'MN_STAFF', freelancerAccessMode: 'default', employmentType: 'probation', probationPeriodMonths: 6 }); setSelectedCompanies([]); setSelectedDepts([]); setSelectedModules([]); setIsModalOpen(true); }}>
                <Plus className="w-4 h-4 mr-2" /> Add Employee
              </Button>
            )}
          </div>
        </CardHeader>
        
        {view === 'list' && (
          <div className="p-4 border-b bg-gray-50 flex flex-wrap gap-2">
            <Input placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
            <select className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
              <option value="">All Roles</option>
              {roles.map(r => <option key={r.id} value={r.id}>{r.name || r.role_name}</option>)}
            </select>
            <select className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
              <option value="">All Departments</option>
              {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <select className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" value={staffTypeFilter} onChange={e => setStaffTypeFilter(e.target.value)}>
              <option value="">All Staff Types</option>
              <option value="MN_STAFF">MN Staff</option>
              <option value="MN_EMPLOYEE">MN Employee</option>
              <option value="FREELANCER">Freelancer</option>
              <option value="MYNT_REAL">Mynt Real</option>
            </select>
            <select className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="deactivated">Deactivated</option>
              <option value="resigned">Resigned</option>
            </select>
          </div>
        )}

        <CardContent className="p-0">
          {view === 'list' ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                  <tr>
                    <th className="px-4 py-3">Employee ID</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Base Company</th>
                    <th className="px-4 py-3">Assigned Companies</th>
                    <th className="px-4 py-3">Department</th>
                    <th className="px-4 py-3">Reports To</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Password Reset</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? <tr><td colSpan={11} className="text-center py-8">Loading...</td></tr> : 
                   filteredEmployees.length === 0 ? <tr><td colSpan={11} className="text-center py-8 text-gray-500">No employees found</td></tr> :
                   filteredEmployees.map(emp => (
                    <tr key={emp.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold">{emp.employee_code || '-'}</td>
                      <td className="px-4 py-3">{emp.full_name}</td>
                      <td className="px-4 py-3">{emp.email || '-'}</td>
                      <td className="px-4 py-3">{emp.role_name || '-'}</td>
                      <td className="px-4 py-3">{emp.base_company_name || '-'}</td>
                      <td className="px-4 py-3 flex flex-wrap gap-1">
                        {emp.data_companies?.length ? emp.data_companies.map((c:any) => <Badge key={c.id||c} variant="secondary">{c.company_name || c.name || `ID:${c.id||c}`}</Badge>) : '-'}
                      </td>
                      <td className="px-4 py-3">{emp.department_name || '-'}</td>
                      <td className="px-4 py-3">{emp.reporting_manager_name || '-'}</td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className={
                          (emp.status || (emp.is_active ? 'active' : 'inactive')) === 'active' ? 'bg-green-100 text-green-800' : 
                          (emp.status || (emp.is_active ? 'active' : 'inactive')) === 'inactive' ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-800'
                        }>
                          {emp.status || (emp.is_active ? 'Active' : 'Inactive')}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Button variant="outline" size="sm" onClick={() => resetPassword(emp.id, emp.id === currentUserId)}>
                          <Key className="w-4 h-4" />
                        </Button>
                      </td>
                      <td className="px-4 py-3 flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEditModal(emp)}><Edit className="w-4 h-4" /></Button>
                        <Button variant="outline" size="sm" className="text-amber-500" onClick={() => { setSelectedEmp(emp); setIsStatusModalOpen(true); }}><PauseCircle className="w-4 h-4" /></Button>
                        <Button variant="outline" size="sm" className="text-red-500" onClick={() => { setSelectedEmp(emp); setIsDeleteModalOpen(true); }}><Trash className="w-4 h-4" /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>Tree View is represented here (migrated to standard hierarchy display).</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Employee Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{formData.id ? 'Edit' : 'Add'} Employee</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
            <div className="space-y-2">
              <Label>First Name *</Label>
              <Input value={formData.firstName} onChange={e => setFormData({...formData, firstName: e.target.value})} required />
            </div>
            <div className="space-y-2">
              <Label>Last Name *</Label>
              <Input value={formData.lastName} onChange={e => setFormData({...formData, lastName: e.target.value})} required />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Role *</Label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={formData.roleId} onChange={e => setFormData({...formData, roleId: e.target.value})} required>
                <option value="">Select Role</option>
                {roles.map(r => <option key={r.id} value={r.id}>{r.name || r.role_name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Primary Department</Label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={formData.departmentId} onChange={e => setFormData({...formData, departmentId: e.target.value})}>
                <option value="">Select Department</option>
                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <Input value={formData.designation} onChange={e => setFormData({...formData, designation: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Date of Joining</Label>
              <Input type="date" value={formData.dateOfJoining} onChange={e => setFormData({...formData, dateOfJoining: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Staff Type</Label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={formData.staffType} onChange={e => setFormData({...formData, staffType: e.target.value})}>
                <option value="MN_STAFF">MN Staff</option>
                <option value="FREELANCER">Freelancer</option>
                <option value="MYNT_REAL">Mynt Staff</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Reporting Manager</Label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={formData.reportingManagerId} onChange={e => setFormData({...formData, reportingManagerId: e.target.value})}>
                <option value="">No Manager</option>
                {employees.filter(e => e.is_active).map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
              </select>
            </div>
            {currentUserRoleCode === 'vgk4u' && (
              <div className="space-y-2">
                <Label>Employee Code</Label>
                <Input value={formData.empCode} onChange={e => setFormData({...formData, empCode: e.target.value})} />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave}>Save Employee</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Status Modal */}
      <Dialog open={isStatusModalOpen} onOpenChange={setIsStatusModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Status</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>Change status for {selectedEmp?.full_name}?</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsStatusModalOpen(false)}>Cancel</Button>
            <Button onClick={changeStatus}>Confirm Change</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Modal */}
      <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Delete Employee</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>Are you sure you want to delete {selectedEmp?.full_name}?</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => deleteEmployee('soft')}>Soft Delete</Button>
            <Button variant="destructive" onClick={() => deleteEmployee('hard')}>Hard Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
"""
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(CONTENT)
print("Employees page created")
