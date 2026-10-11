/** The UI switches on `code`, never on `message` text (Handbook, API standards). */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export const ERROR_CODES = {
  network: 'NETWORK_ERROR',
  unknown: 'UNKNOWN_ERROR',
  invalidCredentials: 'INVALID_CREDENTIALS',
  validationFailed: 'VALIDATION_FAILED',
  slugTaken: 'SLUG_TAKEN',
  emailInUse: 'EMAIL_IN_USE',
  rateLimited: 'RATE_LIMITED',
  resetTokenExpired: 'RESET_TOKEN_EXPIRED',
  invitationInvalid: 'INVITATION_INVALID',
  versionConflict: 'VERSION_CONFLICT',
  authRequired: 'AUTHENTICATION_REQUIRED',
} as const;

export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}
