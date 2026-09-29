import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "../ui/button";

type ErrorStateProps = {
  title: string;
  description: string;
  onRetry?: () => void | Promise<void>;
};

export function ErrorState({ title, description, onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-destructive/30 bg-card p-5">
      <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden="true" />
      <h2 className="mt-3 text-sm font-semibold text-destructive">{title}</h2>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
      {onRetry ? (
        <Button className="mt-4" variant="outline" size="sm" onClick={() => void onRetry()}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Retry
        </Button>
      ) : null}
    </div>
  );
}
