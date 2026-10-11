import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { useToast } from '@/components/ui/Toast';
import { Role } from '@/lib/enums';
import { roleLabel } from '@/lib/labels';

export interface NewEmployeeData {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string;
  status: 'Active' | 'On leave' | 'Invited';
}

const DEPARTMENTS = [
  'Engineering',
  'Design & Creative',
  'Product & Operations',
  'Marketing & Sales',
  'Finance & Accounting',
  'People & HR',
];

const ROLES_LIST = [
  { value: Role.Employee, label: 'Employee' },
  { value: Role.Manager, label: 'Manager' },
  { value: Role.Hr, label: 'HR' },
  { value: Role.Cto, label: 'CTO' },
  { value: Role.Cfo, label: 'CFO' },
  { value: Role.Coo, label: 'COO' },
];

export function AddEmployeeModal({
  open,
  onClose,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  onAdded?: (employee: NewEmployeeData) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<string>(Role.Employee);
  const [department, setDepartment] = useState(DEPARTMENTS[0] as string);
  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; email?: string }>({});

  function validate(): boolean {
    const errs: { name?: string; email?: string } = {};
    if (!name.trim()) {
      errs.name = 'Full name is required';
    } else if (name.trim().length < 2) {
      errs.name = 'Name must be at least 2 characters';
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim()) {
      errs.email = 'Work email is required';
    } else if (!emailRegex.test(email.trim())) {
      errs.email = 'Enter a valid email address';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setPending(true);
    try {
      await new Promise((res) => setTimeout(res, 600));

      const newEmp: NewEmployeeData = {
        id: `emp-${Date.now()}`,
        name: name.trim(),
        email: email.trim().toLowerCase(),
        role: roleLabel(role as Role),
        department,
        status: 'Active',
      };

      onAdded?.(newEmp);
      toast.notify(`Employee ${newEmp.name} added successfully as ${newEmp.role}.`);

      setName('');
      setEmail('');
      setRole(Role.Employee);
      setDepartment(DEPARTMENTS[0] as string);
      setErrors({});
      onClose();
    } catch {
      toast.notify('Failed to add employee. Please try again.', 'error');
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      open={open}
      title="Add new employee"
      description="Create a team profile and issue workspace credentials."
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} noValidate className="mt-2 space-y-4">
        <TextField
          label="Full name"
          name="name"
          placeholder="e.g. Ayesha Malik"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={errors.name}
          required
          icon="user"
        />

        <TextField
          label="Work email"
          type="email"
          name="email"
          placeholder="e.g. ayesha@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
          required
          icon="mail"
        />

        <Select
          label="Assigned role"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          {ROLES_LIST.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </Select>

        <Select
          label="Department"
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
        >
          {DEPARTMENTS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </Select>

        <div className="mt-6 flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose} disabled={pending}>
            Cancel
          </Button>
          <Button type="submit" isLoading={pending} loadingLabel="Adding employee...">
            Save Employee
          </Button>
        </div>
      </form>
    </Modal>
  );
}