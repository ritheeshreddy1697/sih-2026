import {
  BarChart3,
  Award,
  BellRing,
  BookOpen,
  BriefcaseBusiness,
  Building2,
  CalendarRange,
  GraduationCap,
  Handshake,
  LayoutDashboard,
  MessagesSquare,
  ScanLine,
  UserRound,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { PermissionCode } from "./api/client";
import type { TranslationKey } from "../i18n/i18n-provider";

export type NavigationItem = {
  labelKey: TranslationKey;
  href: string;
  icon: LucideIcon;
  permissions?: PermissionCode[];
};

export const navigationItems: NavigationItem[] = [
  { labelKey: "nav.dashboard", href: "/dashboard", icon: LayoutDashboard },
  {
    labelKey: "nav.profile",
    href: "/profile",
    icon: UserRound,
    permissions: ["profiles:self"],
  },
  {
    labelKey: "nav.institutions",
    href: "/directory/institutions",
    icon: Building2,
    permissions: ["profiles:manage_institutions"],
  },
  {
    labelKey: "nav.trainees",
    href: "/directory/trainees",
    icon: UsersRound,
    permissions: ["profiles:view_trainee_directory"],
  },
  {
    labelKey: "nav.notifications",
    href: "/notifications",
    icon: BellRing,
    permissions: ["notifications:send"],
  },
  {
    labelKey: "nav.programmes",
    href: "/programmes",
    icon: BookOpen,
    permissions: ["programmes:view"],
  },
  {
    labelKey: "nav.learning",
    href: "/learning",
    icon: GraduationCap,
    permissions: ["learning:access", "learning:manage"],
  },
  {
    labelKey: "nav.attendance",
    href: "/attendance",
    icon: ScanLine,
    permissions: ["attendance:self", "attendance:manage"],
  },
  {
    labelKey: "nav.operations",
    href: "/operations",
    icon: CalendarRange,
    permissions: ["operations:self", "operations:manage"],
  },
  {
    labelKey: "nav.certificates",
    href: "/certificates",
    icon: Award,
    permissions: ["certificates:self", "certificates:manage"],
  },
  {
    labelKey: "nav.applications",
    href: "/applications",
    icon: GraduationCap,
    permissions: ["applications:apply", "applications:review"],
  },
  {
    labelKey: "nav.nominations",
    href: "/nominations",
    icon: Handshake,
    permissions: ["nominations:create", "applications:review"],
  },
  {
    labelKey: "nav.employment",
    href: "/employment",
    icon: BriefcaseBusiness,
    permissions: ["employment:self", "employment:manage", "employment:verify"],
  },
  {
    labelKey: "nav.career",
    href: "/career-counsellor",
    icon: MessagesSquare,
    permissions: ["career:counselling"],
  },
  {
    labelKey: "nav.analytics",
    href: "/analytics",
    icon: BarChart3,
    permissions: ["analytics:view"],
  },
];
