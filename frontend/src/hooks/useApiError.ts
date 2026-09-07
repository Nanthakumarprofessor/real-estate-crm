/**
 * useApiError — converts an Axios error into a user-friendly string.
 *
 * Maps backend error shapes and HTTP status codes to readable messages.
 * Never exposes raw stack traces or backend internals to the user.
 */
import { isAxiosError } from 'axios';

export function parseApiError(error: unknown): string {
  if (!isAxiosError(error)) {
    return 'An unexpected error occurred. Please try again.';
  }

  const status = error.response?.status;
  const detail: string | undefined = error.response?.data?.detail;

  if (!error.response) {
    return 'Unable to connect to the server. Please check your network.';
  }

  switch (status) {
    case 401:
      return detail ?? 'Invalid email or password.';
    case 403:
      return 'You do not have permission to perform this action.';
    case 422:
      return 'Please check your input and try again.';
    case 500:
      return 'A server error occurred. Please try again later.';
    default:
      return detail ?? `Request failed (${status ?? 'unknown'}).`;
  }
}
