import { useState } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  BriefcaseBusiness,
  Building2,
  GraduationCap,
  Handshake,
  Menu,
  ShieldCheck,
  UserRoundCheck,
  UsersRound,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { Button } from "../components/ui/button";
import { LanguageSelect } from "../components/pwa/language-select";

const audiences = [
  { name: "NCCT", detail: "National oversight and reporting", icon: ShieldCheck },
  { name: "Training institutes", detail: "Programs, batches and trainers", icon: Building2 },
  { name: "Trainers", detail: "Sessions, attendance and assessment", icon: UserRoundCheck },
  { name: "Trainees", detail: "Learning, progress and certificates", icon: GraduationCap },
  { name: "Nominating institutions", detail: "Candidate nominations and outcomes", icon: Handshake },
  { name: "Employers", detail: "Eligible talent and hiring outcomes", icon: BriefcaseBusiness },
];

export function LandingPage() {
  const { user } = useAuth();
  const [navigationOpen, setNavigationOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only z-50 rounded-md bg-card px-4 py-3 text-sm font-medium focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to main content
      </a>
      <header className="relative z-20 border-t-4 border-t-amber-500 bg-card">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <Link className="flex min-w-0 items-center gap-3" to="/" aria-label="NCCT Training Platform home">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <BookOpenCheck className="h-6 w-6" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-sm font-semibold sm:text-base">NCCT Training Platform</span>
              <span className="hidden text-xs text-muted-foreground sm:block">
                National Council for Cooperative Training
              </span>
            </span>
          </Link>

          <nav className="hidden items-center gap-7 lg:flex" aria-label="Public navigation">
            <a className="text-sm font-medium text-muted-foreground hover:text-foreground" href="#participants">
              Participants
            </a>
            <a className="text-sm font-medium text-muted-foreground hover:text-foreground" href="#services">
              Services
            </a>
            <Link className="text-sm font-medium text-muted-foreground hover:text-foreground" to="/login">
              Sign in
            </Link>
            <Button asChild size="sm">
              <Link to={user ? "/dashboard" : "/register"}>
                {user ? "Open dashboard" : "Create account"}
              </Link>
            </Button>
          </nav>

          <div className="flex items-center gap-1">
            <div className="hidden sm:block lg:hidden"><LanguageSelect compact /></div>
            <Button
              className="lg:hidden"
              variant="ghost"
              size="icon"
              aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={navigationOpen}
              aria-controls="public-mobile-navigation"
              onClick={() => setNavigationOpen((current) => !current)}
            >
              {navigationOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>
        {navigationOpen ? (
          <nav
            id="public-mobile-navigation"
            className="border-t bg-card px-4 py-3 lg:hidden"
            aria-label="Mobile public navigation"
          >
            <div className="mx-auto grid max-w-7xl gap-1">
              <div className="sm:hidden"><LanguageSelect /></div>
              <a className="rounded-md px-3 py-3 text-sm font-medium" href="#participants">
                Participants
              </a>
              <a className="rounded-md px-3 py-3 text-sm font-medium" href="#services">
                Services
              </a>
              <Link className="rounded-md px-3 py-3 text-sm font-medium" to="/login">
                Sign in
              </Link>
              <Link className="rounded-md bg-primary px-3 py-3 text-sm font-medium text-primary-foreground" to={user ? "/dashboard" : "/register"}>
                {user ? "Open dashboard" : "Create account"}
              </Link>
            </div>
          </nav>
        ) : null}
      </header>

      <main id="main-content">
        <section className="relative h-[calc(100svh-6rem)] min-h-[470px] max-h-[680px] overflow-hidden bg-foreground text-white">
          <img
            src="/images/cooperative-training-hero.png"
            alt=""
            className="data-heavy-image absolute inset-0 h-full w-full object-cover object-[58%_center]"
          />
          <div className="absolute inset-0 bg-black/55" aria-hidden="true" />
          <div className="relative mx-auto flex h-full max-w-7xl items-center px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl py-10">
              <p className="mb-4 inline-flex rounded-md bg-amber-400 px-3 py-1.5 text-sm font-semibold text-amber-950">
                Cooperative learning across India
              </p>
              <h1 className="text-4xl font-semibold leading-tight tracking-normal sm:text-5xl">
                NCCT Cooperative Training Platform
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-white/85 sm:text-lg">
                One secure place for institutes, trainers, trainees, nominating bodies and employers
                to take cooperative training forward.
              </p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Button asChild size="default" className="h-12 bg-white px-5 text-foreground hover:bg-white/90">
                  <Link to={user ? "/dashboard" : "/login"}>
                    {user ? "Go to dashboard" : "Sign in to continue"}
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
                {!user ? (
                  <Button asChild variant="outline" className="h-12 border-white/60 bg-transparent px-5 text-white hover:bg-white/10">
                    <Link to="/register">Register your account</Link>
                  </Button>
                ) : null}
              </div>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/75">
                <span className="inline-flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                  Secure role-based access
                </span>
                <span className="inline-flex items-center gap-2">
                  <UsersRound className="h-4 w-4 text-amber-300" aria-hidden="true" />
                  Built for the full training network
                </span>
              </div>
            </div>
          </div>
        </section>

        <section id="participants" className="border-b bg-card py-14 sm:py-20">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold text-primary">Connected public service</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-normal sm:text-3xl">
                A clear workspace for every participant
              </h2>
              <p className="mt-3 text-base leading-7 text-muted-foreground">
                Each account opens the information and actions needed for that person’s work.
              </p>
            </div>
            <div className="mt-9 grid gap-x-8 gap-y-7 sm:grid-cols-2 lg:grid-cols-3">
              {audiences.map((audience) => (
                <div key={audience.name} className="flex gap-4 border-t pt-5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted text-primary">
                    <audience.icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold">{audience.name}</h3>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{audience.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="services" className="bg-background py-14 sm:py-20">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-[0.8fr_1.2fr] lg:px-8">
            <div>
              <p className="text-sm font-semibold text-primary">Simple by design</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-normal sm:text-3xl">
                Important work stays easy to find
              </h2>
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="border-l-4 border-l-primary pl-5">
                <h3 className="font-semibold">One account, one clear view</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Dashboards adapt to each role without exposing restricted controls.
                </p>
              </div>
              <div className="border-l-4 border-l-amber-500 pl-5">
                <h3 className="font-semibold">Progress that can be acted on</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Deadlines, statuses and next steps appear in plain language.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t bg-card">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-7 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <p>National Council for Cooperative Training</p>
          <div className="flex gap-5">
            <Link className="inline-flex min-h-11 items-center hover:text-foreground" to="/login">Sign in</Link>
            <Link className="inline-flex min-h-11 items-center hover:text-foreground" to="/register">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
