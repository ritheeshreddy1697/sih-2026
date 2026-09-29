import { BookOpenCheck, CheckCircle2, ShieldCheck } from "lucide-react";

import { LanguageSelect } from "../pwa/language-select";

type AuthLayoutProps = {
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
};

const assurances = [
  "Role-scoped access",
  "Audited sign-in activity",
  "Secure session controls",
];

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <main className="grid min-h-screen bg-card lg:grid-cols-[minmax(320px,0.8fr)_minmax(520px,1.2fr)]">
      <section className="hidden bg-foreground px-10 py-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-md bg-primary">
            <BookOpenCheck className="h-6 w-6" aria-hidden="true" />
          </span>
          <div>
            <p className="font-semibold">NCCT Training Platform</p>
            <p className="text-sm text-white/65">Cooperative education network</p>
          </div>
        </div>

        <div className="max-w-md">
          <ShieldCheck className="mb-5 h-9 w-9 text-emerald-300" aria-hidden="true" />
          <p className="text-3xl font-semibold leading-tight">One secure workspace for every participant.</p>
          <ul className="mt-8 space-y-4 text-sm text-white/75">
            {assurances.map((assurance) => (
              <li key={assurance} className="flex items-center gap-3">
                <CheckCircle2 className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                {assurance}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-white/50">National Council for Cooperative Training</p>
      </section>

      <section className="relative flex min-h-screen items-center justify-center bg-background px-4 py-20 sm:px-8">
        <div className="absolute right-3 top-3 sm:right-6 sm:top-5">
          <LanguageSelect compact />
        </div>
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-white">
              <BookOpenCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <p className="font-semibold">NCCT Training Platform</p>
          </div>

          <div className="rounded-lg border bg-card p-6 shadow-sm sm:p-8">
            <header className="mb-6">
              <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
            </header>
            {children}
          </div>
          {footer ? <div className="mt-5 text-center text-sm text-muted-foreground [&_a]:inline-flex [&_a]:min-h-11 [&_a]:items-center">{footer}</div> : null}
        </div>
      </section>
    </main>
  );
}
