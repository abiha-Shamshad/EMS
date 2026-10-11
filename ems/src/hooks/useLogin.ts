import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { loginRequest } from '@/api/auth';
import { dashboardPathForRole } from '@/lib/permissions';
import { saveSession } from '@/lib/session';

export interface LoginVariables {
  email: string;
  password: string;
  keepSignedIn: boolean;
}

export function useLogin() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (variables: LoginVariables) =>
      loginRequest({ email: variables.email, password: variables.password }),
    onSuccess: (session, variables) => {
      saveSession(session, variables.keepSignedIn);
      navigate(dashboardPathForRole(session.user.role), { replace: true });
    },
  });
}
