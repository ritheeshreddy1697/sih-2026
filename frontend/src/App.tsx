import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/protected-route";
import { AuthProvider } from "./auth/auth-provider";
import { LoadingState } from "./components/states/loading-state";
import { I18nProvider } from "./i18n/i18n-provider";
import { LandingPage } from "./pages/landing-page";
import { PwaProvider } from "./pwa/pwa-provider";

const AdminPage = lazy(() => import("./pages/admin-page").then((module) => ({ default: module.AdminPage })));
const ApplicationsPage = lazy(() => import("./pages/applications-page").then((module) => ({ default: module.ApplicationsPage })));
const AttendanceKioskPage = lazy(() =>
  import("./pages/attendance-kiosk-page").then((module) => ({
    default: module.AttendanceKioskPage,
  })),
);
const AttendancePage = lazy(() =>
  import("./pages/attendance-page").then((module) => ({ default: module.AttendancePage })),
);
const EmploymentPage = lazy(() =>
  import("./pages/employment-page").then((module) => ({ default: module.EmploymentPage })),
);
const CareerCounsellorPage = lazy(() =>
  import("./pages/career-counsellor-page").then((module) => ({
    default: module.CareerCounsellorPage,
  })),
);
const AnalyticsPage = lazy(() =>
  import("./pages/analytics-page").then((module) => ({ default: module.AnalyticsPage })),
);
const CertificateVerificationPage = lazy(() => import("./pages/certificate-verification-page").then((module) => ({ default: module.CertificateVerificationPage })));
const CertificatesPage = lazy(() => import("./pages/certificates-page").then((module) => ({ default: module.CertificatesPage })));
const CourseManagePage = lazy(() => import("./pages/course-manage-page").then((module) => ({ default: module.CourseManagePage })));
const CoursePlayerPage = lazy(() => import("./pages/course-player-page").then((module) => ({ default: module.CoursePlayerPage })));
const DashboardPage = lazy(() => import("./pages/dashboard-page").then((module) => ({ default: module.DashboardPage })));
const ForbiddenPage = lazy(() => import("./pages/forbidden-page").then((module) => ({ default: module.ForbiddenPage })));
const ForgotPasswordPage = lazy(() => import("./pages/forgot-password-page").then((module) => ({ default: module.ForgotPasswordPage })));
const InstitutionDirectoryPage = lazy(() => import("./pages/institution-directory-page").then((module) => ({ default: module.InstitutionDirectoryPage })));
const LearningPage = lazy(() => import("./pages/learning-page").then((module) => ({ default: module.LearningPage })));
const LoginPage = lazy(() => import("./pages/login-page").then((module) => ({ default: module.LoginPage })));
const NominationsPage = lazy(() => import("./pages/nominations-page").then((module) => ({ default: module.NominationsPage })));
const NotificationComposePage = lazy(() => import("./pages/notification-compose-page").then((module) => ({ default: module.NotificationComposePage })));
const OperationsPage = lazy(() => import("./pages/operations-page").then((module) => ({ default: module.OperationsPage })));
const ProfilePage = lazy(() => import("./pages/profile-page").then((module) => ({ default: module.ProfilePage })));
const ProgrammeDetailPage = lazy(() => import("./pages/programme-detail-page").then((module) => ({ default: module.ProgrammeDetailPage })));
const ProgrammeFormPage = lazy(() => import("./pages/programme-form-page").then((module) => ({ default: module.ProgrammeFormPage })));
const ProgrammesPage = lazy(() => import("./pages/programmes-page").then((module) => ({ default: module.ProgrammesPage })));
const RegisterPage = lazy(() => import("./pages/register-page").then((module) => ({ default: module.RegisterPage })));
const ResetPasswordPage = lazy(() => import("./pages/reset-password-page").then((module) => ({ default: module.ResetPasswordPage })));
const TraineeDirectoryPage = lazy(() => import("./pages/trainee-directory-page").then((module) => ({ default: module.TraineeDirectoryPage })));
const TraineeProfileDetailPage = lazy(() => import("./pages/trainee-profile-detail-page").then((module) => ({ default: module.TraineeProfileDetailPage })));
const WorkspacePage = lazy(() => import("./pages/workspace-page").then((module) => ({ default: module.WorkspacePage })));

export function App() {
  return (
    <BrowserRouter>
      <I18nProvider>
        <AuthProvider>
          <PwaProvider>
            <Suspense fallback={<LoadingState label="Loading page" />}>
              <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify/certificate/:token" element={<CertificateVerificationPage />} />
          <Route
            path="/kiosk/attendance"
            element={
              <Suspense fallback={<LoadingState label="Loading attendance kiosk" />}>
                <AttendanceKioskPage />
              </Suspense>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredPermission="platform:manage">
                <AdminPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/learning"
            element={
              <ProtectedRoute requiredAnyPermissions={["learning:access", "learning:manage"]}>
                <LearningPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/learning/courses/:courseId/manage"
            element={
              <ProtectedRoute requiredPermission="learning:manage">
                <CourseManagePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/learning/courses/:courseId"
            element={
              <ProtectedRoute requiredAnyPermissions={["learning:access", "learning:manage"]}>
                <CoursePlayerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/programmes"
            element={
              <ProtectedRoute requiredPermission="programmes:view">
                <ProgrammesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/programmes/new"
            element={
              <ProtectedRoute requiredPermission="programmes:manage">
                <ProgrammeFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/programmes/:programmeId/edit"
            element={
              <ProtectedRoute requiredPermission="programmes:manage">
                <ProgrammeFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/programmes/:programmeId"
            element={
              <ProtectedRoute requiredPermission="programmes:view">
                <ProgrammeDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/attendance"
            element={
              <ProtectedRoute
                requiredAnyPermissions={["attendance:self", "attendance:manage"]}
              >
                <Suspense fallback={<LoadingState label="Loading attendance" />}>
                  <AttendancePage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/operations"
            element={
              <ProtectedRoute
                requiredAnyPermissions={["operations:self", "operations:manage"]}
              >
                <OperationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/certificates"
            element={
              <ProtectedRoute
                requiredAnyPermissions={["certificates:self", "certificates:manage"]}
              >
                <CertificatesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employment"
            element={
              <ProtectedRoute
                requiredAnyPermissions={["employment:self", "employment:manage", "employment:verify"]}
              >
                <Suspense fallback={<LoadingState label="Loading employment exchange" />}>
                  <EmploymentPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/career-counsellor"
            element={
              <ProtectedRoute requiredPermission="career:counselling">
                <Suspense fallback={<LoadingState label="Loading career counsellor" />}>
                  <CareerCounsellorPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute requiredPermission="analytics:view">
                <Suspense fallback={<LoadingState label="Loading analytics" />}>
                  <AnalyticsPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/applications"
            element={
              <ProtectedRoute requiredAnyPermissions={["applications:apply", "applications:review"]}>
                <ApplicationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/nominations"
            element={
              <ProtectedRoute requiredAnyPermissions={["nominations:create", "applications:review"]}>
                <NominationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute requiredPermission="notifications:send">
                <NotificationComposePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute requiredPermission="profiles:self">
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/directory/trainees"
            element={
              <ProtectedRoute requiredPermission="profiles:view_trainee_directory">
                <TraineeDirectoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/directory/trainees/:traineeId"
            element={
              <ProtectedRoute requiredPermission="profiles:view_private">
                <TraineeProfileDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/directory/institutions"
            element={
              <ProtectedRoute requiredPermission="profiles:manage_institutions">
                <InstitutionDirectoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/:section"
            element={
              <ProtectedRoute>
                <WorkspacePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/forbidden"
            element={
              <ProtectedRoute>
                <ForbiddenPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </PwaProvider>
        </AuthProvider>
      </I18nProvider>
    </BrowserRouter>
  );
}
