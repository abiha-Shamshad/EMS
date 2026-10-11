// Fictional sample data for demo mode (VITE_DEMO_MODE=true).
// Clearly separated from real API code: nothing here is sent to a server.
import { Role } from '@/lib/enums';

export const DEMO_USER = {
  id: 'demo-user-sawera',
  name: 'Sawera Ghaffar',
  email: 'sawera@company.com',
  role: Role.Ceo,
};

export interface StatCardDatum {
  id: string;
  label: string;
  value: string;
  icon: 'people' | 'check' | 'doc' | 'dollar';
  footNote: string;
  footBadge?: string;
  footBadgeTone?: 'success' | 'warning';
}

export const DEMO_STATS: StatCardDatum[] = [
  {
    id: 'total-employees',
    label: 'Total employees',
    value: '248',
    icon: 'people',
    footNote: 'vs last month',
    footBadge: '+8.2%',
    footBadgeTone: 'success',
  },
  {
    id: 'present-today',
    label: 'Present today',
    value: '216',
    icon: 'check',
    footNote: '87.1% of workforce',
    footBadge: 'On track',
    footBadgeTone: 'success',
  },
  {
    id: 'active-projects',
    label: 'Active projects',
    value: '18',
    icon: 'doc',
    footNote: '5 nearing deadline',
    footBadge: 'Attention',
    footBadgeTone: 'warning',
  },
  {
    id: 'monthly-revenue',
    label: 'Monthly revenue',
    value: '$184.6K',
    icon: 'dollar',
    footNote: 'vs last month',
    footBadge: '+12%',
    footBadgeTone: 'success',
  },
];

export interface RevenuePoint {
  month: string;
  value: number; // USD
}

export const DEMO_REVENUE: RevenuePoint[] = [
  { month: 'May', value: 78000 },
  { month: 'Jun', value: 112000 },
  { month: 'Jul', value: 98000 },
  { month: 'Aug', value: 152000 },
  { month: 'Sep', value: 178000 },
  { month: 'Oct', value: 208000 },
];

export interface WorkforceSlice {
  label: string;
  count: number;
  color: 'blue' | 'teal' | 'amber' | 'slate';
}

export const DEMO_WORKFORCE: WorkforceSlice[] = [
  { label: 'Engineering', count: 96, color: 'blue' },
  { label: 'Operations', count: 58, color: 'teal' },
  { label: 'Sales & CRM', count: 42, color: 'amber' },
  { label: 'Other teams', count: 52, color: 'slate' },
];

export interface AttentionItem {
  id: string;
  title: string;
  description: string;
  badge: string;
  tone: 'warning' | 'info';
}

export const DEMO_ATTENTION: AttentionItem[] = [
  {
    id: 'deadlines',
    title: '5 projects nearing deadline',
    description: 'Review delivery timelines with project owners',
    badge: 'High priority',
    tone: 'warning',
  },
  {
    id: 'leave',
    title: '12 leave requests awaiting approval',
    description: 'HR has submitted the latest request summary',
    badge: 'Needs review',
    tone: 'warning',
  },
  {
    id: 'onboarding',
    title: 'New team members to onboard',
    description: '3 employees are ready for onboarding',
    badge: 'Get started',
    tone: 'info',
  },
];

export interface ActivityItem {
  id: string;
  title: string;
  description: string;
  time: string;
  tone: 'blue' | 'teal' | 'amber';
}

export const DEMO_ACTIVITY: ActivityItem[] = [
  {
    id: 'phoenix',
    title: 'Project Phoenix updated',
    description: 'Ava Chen changed the project status',
    time: '10 min ago',
    tone: 'blue',
  },
  {
    id: 'new-employee',
    title: 'New employee added',
    description: 'HR added a new team member',
    time: '34 min ago',
    tone: 'teal',
  },
  {
    id: 'quarterly',
    title: 'Quarterly report generated',
    description: 'Finance report is ready to review',
    time: '1 hour ago',
    tone: 'amber',
  },
];

export interface DirectoryMember {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string;
  status: 'Active' | 'On leave' | 'Invited';
}

export const DEMO_DIRECTORY: DirectoryMember[] = [
  { id: '1', name: 'Sawera Ghaffar', email: 'sawera@company.com', role: 'CEO', department: 'Leadership', status: 'Active' },
  { id: '2', name: 'Ava Chen', email: 'ava@company.com', role: 'Manager', department: 'Engineering', status: 'Active' },
  { id: '3', name: 'Bilal Ahmed', email: 'bilal@company.com', role: 'Employee', department: 'Engineering', status: 'Active' },
  { id: '4', name: 'Hina Shah', email: 'hina@company.com', role: 'HR', department: 'People', status: 'On leave' },
  { id: '5', name: 'Omar Siddiqui', email: 'omar@company.com', role: 'CFO', department: 'Finance', status: 'Active' },
  { id: '6', name: 'Ayesha Noor', email: 'ayesha@company.com', role: 'Employee', department: 'Design', status: 'Invited' },
];

export interface DemoProject {
  id: string;
  name: string;
  client: string;
  progress: number;
  due: string;
  status: 'On track' | 'At risk' | 'Nearing deadline';
}

export const DEMO_PROJECTS: DemoProject[] = [
  { id: 'p1', name: 'Project Phoenix', client: 'Northwind Digital', progress: 72, due: 'Oct 24', status: 'Nearing deadline' },
  { id: 'p2', name: 'Website rebuild', client: 'Northwind Digital', progress: 45, due: 'Nov 08', status: 'On track' },
  { id: 'p3', name: 'Contoso support', client: 'Contoso', progress: 90, due: 'Oct 15', status: 'Nearing deadline' },
  { id: 'p4', name: 'Mobile app v2', client: 'Acme Tech', progress: 20, due: 'Dec 01', status: 'On track' },
];

export const INDUSTRY_OPTIONS = [
  'Software & IT services',
  'Healthcare',
  'Education',
  'Retail & E-commerce',
  'Finance & Banking',
  'Manufacturing',
  'Marketing & Media',
  'Other',
];

export const COMPANY_SIZE_OPTIONS = ['1-10', '11-50', '51-200', '201-500', '500+'];

export const TIME_ZONE_OPTIONS = [
  'Asia/Karachi',
  'Asia/Dubai',
  'Europe/London',
  'America/New_York',
  'UTC',
];
