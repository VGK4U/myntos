"use client";

import React, { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Building, CheckCircle, Users, Plus, Edit, Ban, Check, List } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<any>({
    id: '',
    code: '',
    name: '',
    description: '',
    head_id: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [deptRes, empRes] = await Promise.all([
        api.get('/staff/departments'),
        api.get('/staff/employees?status=active')
      ]);
      setDepartments(deptRes.data.departments || deptRes.data || []);
      setEmployees(empRes.data.employees || empRes.data || []);
    } catch (error) {
      console.error('Error fetching data', error);
      toast.error('Failed to load departments');
    } finally {
      setLoading(false);
    }
  };

  const activeDepts = departments.filter(d => d.is_active).length;

  const handleSave = async () => {
    try {
      const isEdit = !!formData.id;
      const url = isEdit ? `/staff/departments/${formData.id}` : '/staff/departments/';
      const method = isEdit ? 'put' : 'post';
      
      const payload = {
        code: formData.code,
        name: formData.name,
        description: formData.description || null,
        head_id: formData.head_id ? parseInt(formData.head_id) : null
      };

      await api[method](url, payload);
      toast.success(isEdit ? 'Department updated' : 'Department added');
      setIsModalOpen(false);
      fetchData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save department');
    }
  };

  const toggleStatus = async (id: number, currentStatus: boolean) => {
    if (!confirm(`Are you sure you want to ${currentStatus ? 'deactivate' : 'activate'} this department?`)) return;
    try {
      await api.put(`/staff/departments/${id}`, { is_active: !currentStatus });
      toast.success('Status updated');
      fetchData();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const openAddModal = () => {
    setFormData({ id: '', code: '', name: '', description: '', head_id: '' });
    setIsModalOpen(true);
  };

  const openEditModal = (dept: any) => {
    setFormData({
      id: dept.id,
      code: dept.code,
      name: dept.name,
      description: dept.description || '',
      head_id: dept.head_id || ''
    });
    setIsModalOpen(true);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex items-center p-4">
          <div className="h-12 w-12 rounded-lg bg-blue-500 text-white flex items-center justify-center mr-4">
            <Building className="h-6 w-6" />
          </div>
          <div>
            <div className="text-3xl font-bold">{departments.length}</div>
            <div className="text-sm text-gray-500">Total Departments</div>
          </div>
        </Card>
        <Card className="flex items-center p-4">
          <div className="h-12 w-12 rounded-lg bg-green-500 text-white flex items-center justify-center mr-4">
            <CheckCircle className="h-6 w-6" />
          </div>
          <div>
            <div className="text-3xl font-bold">{activeDepts}</div>
            <div className="text-sm text-gray-500">Active Departments</div>
          </div>
        </Card>
        <Card className="flex items-center p-4">
          <div className="h-12 w-12 rounded-lg bg-orange-500 text-white flex items-center justify-center mr-4">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <div className="text-3xl font-bold">{employees.length}</div>
            <div className="text-sm text-gray-500">Total Employees</div>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-xl flex items-center gap-2">
            <List className="h-5 w-5" /> All Departments
          </CardTitle>
          <Button onClick={openAddModal}>
            <Plus className="h-4 w-4 mr-2" /> Add Department
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3">Department Code</th>
                  <th className="px-4 py-3">Department Name</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Head</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Employees</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8">Loading...</td>
                  </tr>
                ) : departments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500">No departments found</td>
                  </tr>
                ) : (
                  departments.map(dept => (
                    <tr key={dept.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold">{dept.code}</td>
                      <td className="px-4 py-3">{dept.name}</td>
                      <td className="px-4 py-3">{dept.description || '-'}</td>
                      <td className="px-4 py-3">{dept.head_name || '-'}</td>
                      <td className="px-4 py-3">
                        <Badge variant={dept.is_active ? 'default' : 'destructive'} className={dept.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {dept.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">{dept.employee_count || 0}</td>
                      <td className="px-4 py-3 flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEditModal(dept)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm" className="text-red-500" onClick={() => toggleStatus(dept.id, dept.is_active)}>
                          {dept.is_active ? <Ban className="h-4 w-4" /> : <Check className="h-4 w-4 text-green-500" />}
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{formData.id ? 'Edit' : 'Add'} Department</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Department Code *</Label>
              <Input placeholder="e.g., HR, IT, FIN" value={formData.code} onChange={e => setFormData({...formData, code: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Department Name *</Label>
              <Input placeholder="e.g., Human Resources" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea placeholder="Brief description..." value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
            </div>
            <div className="space-y-2">
              <Label>Department Head</Label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={formData.head_id} onChange={e => setFormData({...formData, head_id: e.target.value})}>
                <option value="">Select Head (Optional)</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>{emp.full_name} ({emp.emp_code || emp.employee_code || 'N/A'})</option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave}>Save Department</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
