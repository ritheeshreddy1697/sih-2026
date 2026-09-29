type LoadingStateProps = {
  label?: string;
};

export function LoadingState({ label = "Loading" }: LoadingStateProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card p-4 text-sm text-muted-foreground">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-r-transparent"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}

