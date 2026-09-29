import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bell,
  BookOpenCheck,
  ChevronDown,
  CircleUserRound,
  Download,
  LogOut,
  Menu,
  RefreshCw,
  Settings,
  Settings2,
  Smartphone,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../../auth/auth-context-value";
import { useI18n } from "../../i18n/i18n-provider";
import {
  apiClient,
  type DashboardNotification,
  type NotificationItem,
  type User,
} from "../../lib/api/client";
import { navigationItems } from "../../lib/navigation";
import { cn } from "../../lib/utils";
import { usePwa } from "../../pwa/pwa-provider";
import { LanguageSelect } from "../pwa/language-select";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

type AppShellProps = {
  children: React.ReactNode;
  user: User;
  onLogout: () => Promise<void>;
  notifications?: DashboardNotification[];
};

export function AppShell({ children, user, onLogout, notifications = [] }: AppShellProps) {
  const { canAny } = useAuth();
  const { t } = useI18n();
  const {
    isOnline,
    isReducedData,
    setReducedData,
    queueCount,
    downloadCount,
    isSyncing,
    installAvailable,
    updateAvailable,
    syncProgress,
    install,
    applyUpdate,
  } = usePwa();
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [deliveredNotifications, setDeliveredNotifications] = useState<NotificationItem[]>([]);
  const firstMobileLink = useRef<HTMLAnchorElement>(null);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const visibleNotifications = useMemo<Array<DashboardNotification | NotificationItem>>(() => {
    const deliveredIds = new Set(deliveredNotifications.map((notification) => notification.id));
    return [
      ...deliveredNotifications,
      ...notifications.filter((notification) => !deliveredIds.has(notification.id)),
    ];
  }, [deliveredNotifications, notifications]);
  const unreadCount = visibleNotifications.filter((notification) => notification.unread).length;
  const visibleNavigation = useMemo(
    () => navigationItems.filter((item) => !item.permissions || canAny(item.permissions)),
    [canAny],
  );

  useEffect(() => {
    if (mobileNavigationOpen) firstMobileLink.current?.focus();
  }, [mobileNavigationOpen]);

  useEffect(() => {
    let active = true;
    void apiClient.notifications()
      .then((result) => {
        if (active && Array.isArray(result.items)) setDeliveredNotifications(result.items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const closeMenus = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setMobileNavigationOpen(false);
      setNotificationsOpen(false);
      setProfileOpen(false);
      setPreferencesOpen(false);
    };
    window.addEventListener("keydown", closeMenus);
    return () => window.removeEventListener("keydown", closeMenus);
  }, []);

  useEffect(() => {
    if (!notificationsOpen) return;
    const closeNotifications = (event: PointerEvent) => {
      if (!notificationsRef.current?.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeNotifications);
    return () => document.removeEventListener("pointerdown", closeNotifications);
  }, [notificationsOpen]);

  const markNotificationRead = (notification: DashboardNotification | NotificationItem) => {
    if (!("sender_name" in notification) || !notification.unread) return;
    setDeliveredNotifications((current) =>
      current.map((item) => item.id === notification.id ? { ...item, unread: false } : item),
    );
    void apiClient.markNotificationRead(notification.id).catch(() => {
      setDeliveredNotifications((current) =>
        current.map((item) => item.id === notification.id ? { ...item, unread: true } : item),
      );
    });
  };

  const navigation = (mobile = false) => (
    <nav className="space-y-1" aria-label={mobile ? "Mobile workspace navigation" : "Workspace navigation"}>
      {visibleNavigation.map((item, index) => (
        <NavLink
          ref={mobile && index === 0 ? firstMobileLink : undefined}
          key={item.href}
          to={item.href}
          onClick={() => setMobileNavigationOpen(false)}
          className={({ isActive }) =>
            cn(
              "flex min-h-11 items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )
          }
        >
          <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
          {t(item.labelKey)}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-background">
      <a
        href="#workspace-content"
        className="sr-only z-50 rounded-md bg-card px-4 py-3 text-sm font-medium focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:ring-2 focus:ring-primary"
      >
        {t("common.skipWorkspace")}
      </a>

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r bg-card lg:flex lg:flex-col">
        <Link className="flex h-20 items-center gap-3 border-b px-5" to="/dashboard">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BookOpenCheck className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">{t("brand.name")}</span>
            <span className="block truncate text-xs text-muted-foreground">{t("brand.network")}</span>
          </span>
        </Link>
        <div className="flex-1 overflow-y-auto px-3 py-5">{navigation()}</div>
        <div className="border-t p-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted text-sm font-semibold text-primary">
              {(user.profile?.full_name ?? user.email).charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user.profile?.full_name ?? user.email}</p>
              <p className="truncate text-xs text-muted-foreground">{user.roles[0]?.display_name}</p>
            </div>
          </div>
        </div>
      </aside>

      {mobileNavigationOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            className="absolute inset-0 bg-foreground/45"
            aria-label={t("common.closeNavigation")}
            onClick={() => setMobileNavigationOpen(false)}
          />
          <aside className="relative flex h-full w-[min(86vw,320px)] flex-col border-r bg-card shadow-xl" role="dialog" aria-modal="true" aria-label="Workspace navigation">
            <div className="flex h-16 items-center justify-between border-b px-4 py-3">
              <Link className="flex items-center gap-3" to="/dashboard" onClick={() => setMobileNavigationOpen(false)}>
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <BookOpenCheck className="h-5 w-5" aria-hidden="true" />
                </span>
                <span className="text-sm font-semibold">{t("brand.name")}</span>
              </Link>
              <Button variant="ghost" size="icon" onClick={() => setMobileNavigationOpen(false)} aria-label={t("common.closeNavigation")}>
                <X className="h-5 w-5" aria-hidden="true" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-4">{navigation(true)}</div>
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-card/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <Button
              className="lg:hidden"
              variant="ghost"
              size="icon"
              aria-label={t("common.openNavigation")}
              aria-expanded={mobileNavigationOpen}
              onClick={() => setMobileNavigationOpen(true)}
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </Button>
            <div className="hidden sm:block">
              <p className="text-xs text-muted-foreground">{t("common.signedInAs")}</p>
              <p className="text-sm font-medium">{user.roles[0]?.display_name}</p>
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            <div
              className={cn(
                "flex h-11 min-w-11 items-center justify-center gap-2 rounded-md px-2 text-xs font-medium",
                isOnline ? "text-emerald-800" : "bg-amber-100 text-amber-950",
              )}
              role="status"
              aria-live="polite"
              aria-label={isOnline ? t("pwa.online") : t("pwa.offline")}
            >
              {isOnline ? <Wifi className="h-4 w-4" aria-hidden="true" /> : <WifiOff className="h-4 w-4" aria-hidden="true" />}
              <span className="hidden md:inline">{isOnline ? t("pwa.online") : t("pwa.offline")}</span>
              {queueCount ? <span className="rounded-full bg-amber-200 px-1.5 py-0.5 text-[11px] text-amber-950">{queueCount}</span> : null}
            </div>

            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                aria-label="App preferences"
                aria-expanded={preferencesOpen}
                aria-controls="app-preferences-panel"
                onClick={() => {
                  setPreferencesOpen((current) => !current);
                  setNotificationsOpen(false);
                  setProfileOpen(false);
                }}
              >
                <Settings2 className="h-5 w-5" aria-hidden="true" />
              </Button>
              {preferencesOpen ? (
                <div id="app-preferences-panel" className="absolute right-0 mt-2 w-[min(88vw,340px)] rounded-lg border bg-card p-3 shadow-lg" role="dialog" aria-label="App preferences">
                  <p className="px-1 text-sm font-semibold">App preferences</p>
                  <div className="mt-2 border-t pt-2"><LanguageSelect /></div>
                  <label className="mt-1 flex min-h-12 cursor-pointer items-start gap-3 rounded-md px-3 py-2 hover:bg-muted">
                    <input className="mt-1 h-5 w-5 accent-primary" type="checkbox" checked={isReducedData} onChange={(event) => setReducedData(event.target.checked)} />
                    <span><span className="block text-sm font-medium">{t("pwa.reducedData")}</span><span className="mt-0.5 block text-xs leading-5 text-muted-foreground">{t("pwa.reducedDataHint")}</span></span>
                  </label>
                  <div className="mt-2 border-t pt-2 text-xs text-muted-foreground">
                    <p className="flex min-h-9 items-center gap-2 px-3"><Download className="h-4 w-4" aria-hidden="true" />{downloadCount} offline files</p>
                    {queueCount ? <p className="px-3 py-1">{t("pwa.queued", { count: queueCount })}</p> : null}
                  </div>
                  {queueCount ? <Button className="mt-2 w-full" variant="outline" disabled={!isOnline || isSyncing} onClick={() => void syncProgress()}><RefreshCw className={cn("h-4 w-4", isSyncing && "animate-spin")} aria-hidden="true" />{isSyncing ? t("pwa.syncing") : t("pwa.sync")}</Button> : null}
                  {installAvailable ? <Button className="mt-2 w-full" variant="outline" onClick={() => void install()}><Smartphone className="h-4 w-4" aria-hidden="true" />{t("pwa.install")}</Button> : null}
                  {updateAvailable ? <Button className="mt-2 w-full" onClick={applyUpdate}><RefreshCw className="h-4 w-4" aria-hidden="true" />{t("pwa.update")}</Button> : null}
                </div>
              ) : null}
            </div>

            <div className="relative" ref={notificationsRef}>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`${t("common.notifications")}${unreadCount ? `, ${unreadCount} ${t("common.unread")}` : ""}`}
                aria-expanded={notificationsOpen}
                aria-controls="notification-panel"
                onClick={() => {
                  setNotificationsOpen((current) => !current);
                  setProfileOpen(false);
                  setPreferencesOpen(false);
                }}
              >
                <Bell className="h-5 w-5" aria-hidden="true" />
                {unreadCount ? (
                  <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-amber-950">
                    {unreadCount}
                  </span>
                ) : null}
              </Button>
              {notificationsOpen ? (
                <div id="notification-panel" className="absolute right-0 mt-2 w-[min(88vw,360px)] rounded-lg border bg-card p-2 shadow-lg" role="region" aria-label="Notifications">
                  <div className="flex items-center justify-between px-2 py-2">
                    <p className="text-sm font-semibold">{t("common.notifications")}</p>
                    <Badge>{unreadCount} {t("common.unread")}</Badge>
                  </div>
                  {visibleNotifications.length ? (
                    <ul className="max-h-80 overflow-y-auto">
                      {visibleNotifications.map((notification) => (
                        <li key={notification.id} className="border-t px-2 py-3 first:border-t-0">
                          <button
                            type="button"
                            className="flex w-full gap-3 text-left"
                            onClick={() => markNotificationRead(notification)}
                          >
                            <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", notification.unread ? "bg-primary" : "bg-border")} aria-hidden="true" />
                            <div>
                              <p className="text-sm font-medium">{notification.title}</p>
                              <p className="mt-1 text-xs leading-5 text-muted-foreground">{notification.description}</p>
                              {"sender_name" in notification ? <p className="mt-1 text-xs text-muted-foreground">From {notification.sender_name}</p> : null}
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="px-2 py-6 text-center text-sm text-muted-foreground">{t("common.noNotifications")}</p>
                  )}
                </div>
              ) : null}
            </div>

            <div className="relative">
              <Button
                variant="ghost"
                className="h-11 gap-2 px-2 sm:px-3"
                aria-label={t("common.openProfile")}
                aria-expanded={profileOpen}
                aria-controls="profile-menu"
                onClick={() => {
                  setProfileOpen((current) => !current);
                  setNotificationsOpen(false);
                  setPreferencesOpen(false);
                }}
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-sm font-semibold text-primary">
                  {(user.profile?.full_name ?? user.email).charAt(0).toUpperCase()}
                </span>
                <span className="hidden max-w-36 truncate text-sm sm:inline">{user.profile?.full_name ?? user.email}</span>
                <ChevronDown className="hidden h-4 w-4 text-muted-foreground sm:block" aria-hidden="true" />
              </Button>
              {profileOpen ? (
                <div id="profile-menu" className="absolute right-0 mt-2 w-64 rounded-lg border bg-card p-2 shadow-lg" role="menu">
                  <div className="border-b px-2 py-2">
                    <p className="truncate text-sm font-medium">{user.profile?.full_name ?? user.email}</p>
                    <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                  </div>
                  <Link className="mt-1 flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm hover:bg-muted" to={canAny(["profiles:self"]) ? "/profile" : "/workspace/profile"} role="menuitem" onClick={() => setProfileOpen(false)}>
                    <CircleUserRound className="h-4 w-4" aria-hidden="true" />
                    {t("common.profile")}
                  </Link>
                  <Link className="flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm hover:bg-muted" to="/workspace/settings" role="menuitem" onClick={() => setProfileOpen(false)}>
                    <Settings className="h-4 w-4" aria-hidden="true" />
                    {t("common.settings")}
                  </Link>
                  <button className="flex min-h-11 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-destructive hover:bg-destructive/5" type="button" role="menuitem" onClick={() => void onLogout()}>
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    {t("common.signOut")}
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main id="workspace-content" className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
