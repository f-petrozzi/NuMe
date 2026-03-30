import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import AppLayout from "@/components/AppLayout";

import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import OnboardingPage from "@/pages/OnboardingPage";
import MemberDashboard from "@/pages/MemberDashboard";
import HealthDashboard from "@/pages/HealthDashboard";
import CoordinatorDashboard from "@/pages/CoordinatorDashboard";
import ScenarioRunner from "@/pages/ScenarioRunner";
import TraceView from "@/pages/TraceView";
import TracesListPage from "@/pages/TracesListPage";
import CheckInPage from "@/pages/CheckInPage";
import RecipeListPage from "@/pages/RecipeListPage";
import RecipeDetailPage from "@/pages/RecipeDetailPage";
import NotFound from "@/pages/NotFound";
import type { User } from "@/lib/types";

const queryClient = new QueryClient();

function isStaff(user: User | null | undefined) {
  return user?.role === "coordinator" || user?.role === "admin";
}

function getHomeRoute(user: User | null | undefined) {
  if (!user) return "/login";
  if (user.role === "admin") return "/traces";
  if (user.role === "coordinator") return "/coordinator";
  return user.onboarded ? "/dashboard" : "/onboarding";
}

function MemberRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "member") return <Navigate to={getHomeRoute(user)} replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function StaffRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (!isStaff(user)) return <Navigate to={getHomeRoute(user)} replace />;
  return <AppLayout>{children}</AppLayout>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to={getHomeRoute(user)} replace />;
  return <AppLayout>{children}</AppLayout>;
}

function AppRoutes() {
  const { user, isLoading, authError, retrySessionSync, logout } = useAuth();
  if (isLoading) return null;
  if (authError) {
    return (
      <Routes>
        <Route
          path="*"
          element={
            <div className="flex min-h-screen items-center justify-center bg-background px-6 text-foreground">
              <div className="max-w-xl rounded-2xl border border-border bg-card p-8 shadow-sm">
                <h1 className="text-2xl font-semibold">Backend auth sync failed</h1>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{authError}</p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Common local causes are a missing backend Clerk secret, an origin that is not listed in
                  <code> CLERK_AUTHORIZED_PARTIES</code>, or the backend being unavailable.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button onClick={retrySessionSync}>Retry session sync</Button>
                  <Button variant="outline" onClick={logout}>Sign out</Button>
                </div>
              </div>
            </div>
          }
        />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login/*" element={user ? <Navigate to={getHomeRoute(user)} /> : <LoginPage />} />
      <Route path="/register/*" element={user ? <Navigate to={getHomeRoute(user)} /> : <RegisterPage />} />
      <Route path="/onboarding" element={user ? (user.role !== "member" || user.onboarded ? <Navigate to={getHomeRoute(user)} replace /> : <OnboardingPage />) : <Navigate to="/login" />} />
      <Route path="/dashboard" element={<MemberRoute><MemberDashboard /></MemberRoute>} />
      <Route path="/health" element={<MemberRoute><HealthDashboard /></MemberRoute>} />
      <Route path="/check-in" element={<MemberRoute><CheckInPage /></MemberRoute>} />
      <Route path="/recipes" element={<MemberRoute><RecipeListPage /></MemberRoute>} />
      <Route path="/recipes/:id" element={<MemberRoute><RecipeDetailPage /></MemberRoute>} />
      <Route path="/coordinator" element={<StaffRoute><CoordinatorDashboard /></StaffRoute>} />
      <Route path="/scenarios" element={<AdminRoute><ScenarioRunner /></AdminRoute>} />
      <Route path="/traces" element={<AdminRoute><TracesListPage /></AdminRoute>} />
      <Route path="/traces/:runId" element={<AdminRoute><TraceView /></AdminRoute>} />
      <Route path="/" element={<Navigate to={getHomeRoute(user)} replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <AuthProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
