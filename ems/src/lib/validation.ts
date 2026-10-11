// Shared validation. Every rule below comes from the Release 1 spec
// (API-002 signup, API-005/006 password reset, API-010 company setup,
// API-011 invitations) or the copy shown on the design frames.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const URL_PATTERN = /^https?:\/\/[^\s/$.?#].[^\s]*$/i;

const COMMON_PASSWORDS = new Set([
  'password',
  'password123',
  '12345678',
  'qwerty123',
  'letmein123',
  'welcome123',
  'admin123456',
  'ems12345678',
]);

export interface FieldErrors {
  [field: string]: string | undefined;
}

export function hasErrors(errors: FieldErrors): boolean {
  return Object.values(errors).some((message) => message !== undefined);
}

export function validateEmailField(value: string, label = 'work email'): string | undefined {
  const email = value.trim();
  if (!email) return `Enter your ${label}.`;
  if (email.length > 254) return 'That email address is too long.';
  if (!EMAIL_PATTERN.test(email)) return 'Enter a valid email address.';
  return undefined;
}

function validatePassword(value: string, fieldLabel: string): string | undefined {
  if (!value) return `Enter ${fieldLabel}.`;
  if (value.length < 12) return 'Use at least 12 characters.';
  if (value.length > 128) return 'Use at most 128 characters.';
  if (COMMON_PASSWORDS.has(value.toLowerCase())) return 'That password is too common. Try a longer passphrase.';
  return undefined;
}

// --- Login (API-003) -------------------------------------------------

export interface LoginFieldErrors {
  email?: string;
  password?: string;
}

export function validateLogin(email: string, password: string): LoginFieldErrors {
  const errors: LoginFieldErrors = {};
  const emailError = validateEmailField(email);
  if (emailError) errors.email = emailError;
  if (!password) errors.password = 'Enter your password.';
  return errors;
}

// --- Create company account (API-002, EMS_Screen_02) ------------------

export interface RegisterFieldErrors extends FieldErrors {
  companyName?: string;
  email?: string;
  password?: string;
  terms?: string;
}

export function validateRegister(input: {
  companyName: string;
  email: string;
  password: string;
  agreedToTerms: boolean;
}): RegisterFieldErrors {
  const errors: RegisterFieldErrors = {};
  if (!input.companyName.trim()) errors.companyName = 'Enter your company name.';
  else if (input.companyName.trim().length > 120) errors.companyName = 'Keep the company name under 120 characters.';
  const emailError = validateEmailField(input.email);
  if (emailError) errors.email = emailError;
  const passwordError = validatePassword(input.password, 'a password');
  if (passwordError) errors.password = passwordError;
  if (!input.agreedToTerms) errors.terms = 'Please agree to the Terms of Service and Privacy Policy.';
  return errors;
}

// --- Forgot password (API-005, EMS_Screen_03) -------------------------

export interface ForgotPasswordFieldErrors {
  email?: string;
}

export function validateForgotPassword(email: string): ForgotPasswordFieldErrors {
  const errors: ForgotPasswordFieldErrors = {};
  const emailError = validateEmailField(email);
  if (emailError) errors.email = emailError;
  return errors;
}

// --- Reset password (API-006, EMS_Screen_04) --------------------------
// Design checklist on the frame: 8+ chars, upper, lower, number, special.

function checkPasswordRule(value: string, rule: 'length' | 'upper' | 'lower' | 'number' | 'special'): boolean {
  switch (rule) {
    case 'length':
      return value.length >= 8;
    case 'upper':
      return /[A-Z]/.test(value);
    case 'lower':
      return /[a-z]/.test(value);
    case 'number':
      return /[0-9]/.test(value);
    case 'special':
      return /[^A-Za-z0-9]/.test(value);
  }
}

export interface PasswordChecklist {
  length: boolean;
  upper: boolean;
  lower: boolean;
  number: boolean;
  special: boolean;
}

export function passwordChecklist(value: string): PasswordChecklist {
  return {
    length: checkPasswordRule(value, 'length'),
    upper: checkPasswordRule(value, 'upper'),
    lower: checkPasswordRule(value, 'lower'),
    number: checkPasswordRule(value, 'number'),
    special: checkPasswordRule(value, 'special'),
  };
}

export type PasswordStrength = 'weak' | 'medium' | 'strong' | 'very-strong';

export function passwordStrength(value: string): PasswordStrength {
  const met = Object.values(passwordChecklist(value)).filter(Boolean).length;
  if (value.length >= 12 && met === 5) return 'very-strong';
  if (met >= 4) return 'strong';
  if (met >= 2) return 'medium';
  return 'weak';
}

export const PASSWORD_STRENGTH_LABELS: Record<PasswordStrength, string> = {
  weak: 'Weak',
  medium: 'Medium Strength',
  strong: 'Strong',
  'very-strong': 'Very Strong',
};

export interface ResetPasswordFieldErrors {
  password?: string;
  confirmPassword?: string;
}

export function validateResetPassword(password: string, confirmPassword: string): ResetPasswordFieldErrors {
  const errors: ResetPasswordFieldErrors = {};
  const checklist = passwordChecklist(password);
  if (!password) errors.password = 'Enter a new password.';
  else if (!Object.values(checklist).every(Boolean))
    errors.password = 'Your password must meet every rule in the checklist.';
  if (!confirmPassword) errors.confirmPassword = 'Confirm your new password.';
  else if (password && confirmPassword !== password) errors.confirmPassword = 'Passwords do not match.';
  return errors;
}

// --- Company setup (API-010, EMS_Screen_05) ----------------------------

export interface CompanySetupFieldErrors extends FieldErrors {
  companyName?: string;
  industry?: string;
  companySize?: string;
  companyWebsite?: string;
  timeZone?: string;
  about?: string;
}

export const MAX_ABOUT_LENGTH = 500;

export function validateCompanySetup(input: {
  companyName: string;
  industry: string;
  companySize: string;
  companyWebsite: string;
  timeZone: string;
  about: string;
}): CompanySetupFieldErrors {
  const errors: CompanySetupFieldErrors = {};
  if (!input.companyName.trim()) errors.companyName = 'Enter your company name.';
  if (!input.industry.trim()) errors.industry = 'Select your industry.';
  if (!input.companySize.trim()) errors.companySize = 'Select your company size.';
  if (!input.timeZone.trim()) errors.timeZone = 'Select your time zone.';
  const website = input.companyWebsite.trim();
  if (website && !URL_PATTERN.test(website)) errors.companyWebsite = 'Enter a valid URL starting with http(s)://.';
  if (input.about.trim().length > MAX_ABOUT_LENGTH)
    errors.about = `Keep it under ${MAX_ABOUT_LENGTH} characters.`;
  return errors;
}

// --- Invite team (API-011, EMS_Screen_06) ------------------------------
// Max 20 rows; roles from the shared enum; message max 300 characters.

export const MAX_INVITE_ROWS = 20;
export const MAX_INVITE_MESSAGE_LENGTH = 300;

export interface InviteRow {
  id: string;
  email: string;
  role: string;
}

export interface InviteFieldErrors {
  rows: Array<{ email?: string }>;
  message?: string;
  form?: string;
}

export function validateInvites(rows: InviteRow[], message: string): InviteFieldErrors {
  const errors: InviteFieldErrors = { rows: rows.map(() => ({})) };
  const seen = new Set<string>();
  rows.forEach((row, index) => {
    const email = row.email.trim().toLowerCase();
    if (!row.email.trim()) {
      errors.rows[index] = { email: 'Enter an email address.' };
    } else if (!EMAIL_PATTERN.test(email)) {
      errors.rows[index] = { email: 'Enter a valid email address.' };
    } else if (seen.has(email)) {
      errors.rows[index] = { email: 'This email is already added.' };
    } else {
      seen.add(email);
    }
    if (!row.role) {
      errors.form = 'Every invite needs a role.';
    }
  });
  if (message.length > MAX_INVITE_MESSAGE_LENGTH)
    errors.message = `Keep your message under ${MAX_INVITE_MESSAGE_LENGTH} characters.`;
  return errors;
}

export function inviteHasErrors(errors: InviteFieldErrors): boolean {
  return (
    errors.form !== undefined ||
    errors.message !== undefined ||
    errors.rows.some((row) => row.email !== undefined)
  );
}

// --- Misc -------------------------------------------------------------

export function slugifyCompanyName(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'company'
  );
}

export function isValidSlug(value: string): boolean {
  return SLUG_PATTERN.test(value);
}
