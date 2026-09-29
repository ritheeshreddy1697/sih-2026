import { type FormEvent, useState } from "react";
import { CheckCircle2, KeyRound } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { AuthLayout } from "../components/auth/auth-layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ApiError, apiClient } from "../lib/api/client";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(token ? null : "A reset token is required.");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await apiClient.confirmPasswordReset(token, password);
      setMessage(result.message);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to update the password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Choose a new password"
      description="Use at least 12 characters. Existing sessions will be signed out."
      footer={<Link className="font-medium text-primary hover:underline" to="/login">Return to sign in</Link>}
    >
      {message ? (
        <div className="space-y-5 text-center" aria-live="polite">
          <CheckCircle2 className="mx-auto h-9 w-9 text-primary" aria-hidden="true" />
          <p className="text-sm leading-6 text-muted-foreground">{message}</p>
          <Button asChild className="w-full"><Link to="/login">Sign in</Link></Button>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit}>
          {error ? <p className="text-sm text-destructive" role="alert">{error}</p> : null}
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="new-password">New password</label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="confirm-password">Confirm password</label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
          </div>
          <Button className="w-full" type="submit" disabled={isSubmitting || !token}>
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? "Updating..." : "Update password"}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
