import { type FormEvent, useState } from "react";
import { ArrowLeft, KeyRound } from "lucide-react";
import { Link } from "react-router-dom";

import { AuthLayout } from "../components/auth/auth-layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ApiError, apiClient } from "../lib/api/client";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await apiClient.requestPasswordReset(email);
      setMessage(result.message);
      setResetToken(result.reset_token);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to start password reset.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Reset your password"
      description="Enter your account email to request a time-limited reset token."
      footer={
        <Link className="inline-flex items-center gap-2 font-medium text-primary hover:underline" to="/login">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to sign in
        </Link>
      }
    >
      {message ? (
        <div className="space-y-4" aria-live="polite">
          <p className="rounded-md border bg-muted p-4 text-sm leading-6">{message}</p>
          {resetToken ? (
            <Button asChild className="w-full">
              <Link to={`/reset-password?token=${encodeURIComponent(resetToken)}`}>
                <KeyRound className="h-4 w-4" aria-hidden="true" />
                Continue with development token
              </Link>
            </Button>
          ) : null}
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit}>
          {error ? <p className="text-sm text-destructive" role="alert">{error}</p> : null}
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="reset-email">
              Email address
            </label>
            <Input
              id="reset-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <Button className="w-full" type="submit" disabled={isSubmitting}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? "Requesting..." : "Request reset"}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
