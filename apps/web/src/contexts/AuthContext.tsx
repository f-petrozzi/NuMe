import axios from "axios";
import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth as useClerkAuth, useClerk, useUser } from "@clerk/clerk-react";

import { getStoredUser, refreshSessionUser } from "@/lib/api";
import { clearStoredSession, setAccessTokenProvider, setDemoHeader, setStoredUser } from "@/lib/api-client";
import { appConfig } from "@/lib/config";
import type { User } from "@/lib/types";

const DEMO_PRIVILEGED_EMAILS = new Set(["petrozzi.fabrizio@gmail.com", "337401@gmail.com"]);
const DEMO_EMAIL_STORAGE_KEY = "nume_demo_as";

interface AuthContextValue {
  user: User | null;
  setUser: (u: User | null) => void;
  retrySessionSync: () => void;
  logout: () => void;
  isLoading: boolean;
  authError: string | null;
  isDemoMode: boolean;
  demoEmail: string | null;
  isPrivilegedUser: boolean;
  switchDemoUser: (email: string) => void;
  exitDemo: () => void;
}

type ClerkUser = NonNullable<ReturnType<typeof useUser>["user"]>;

const AuthContext = createContext<AuthContextValue>({
  user: null,
  setUser: () => {},
  retrySessionSync: () => {},
  logout: () => {},
  isLoading: true,
  authError: null,
  isDemoMode: false,
  demoEmail: null,
  isPrivilegedUser: false,
  switchDemoUser: () => {},
  exitDemo: () => {},
});

export const useAuth = () => useContext(AuthContext);

function inferNameFromIdentifier(identifier: string): string {
  const local = identifier.split("@")[0] || "NüMe User";
  return local
    .replace(/[._+]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function readMetadata(user: ClerkUser, key: string): unknown {
  return user.publicMetadata?.[key] ?? user.unsafeMetadata?.[key];
}

function describeAuthSyncError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail =
      error.response?.data && typeof error.response.data === "object" ? error.response.data.detail : undefined;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
    if (error.response?.status) {
      return `Backend auth sync failed with status ${error.response.status}.`;
    }
    if (error.message) {
      return `Backend auth sync failed: ${error.message}`;
    }
  }

  return "Backend auth sync failed. Verify the backend is running and Clerk is configured.";
}

function mapClerkUser(user: ClerkUser): User {
  const email = user.primaryEmailAddress?.emailAddress || user.emailAddresses[0]?.emailAddress || null;
  const username = user.username || null;
  const identifier = username || email || "NüMe User";
  const rawPersona = readMetadata(user, "persona_type");
  const rawOnboarded = readMetadata(user, "onboarded");

  return {
    id: user.id,
    username,
    email,
    full_name:
      user.fullName || [user.firstName, user.lastName].filter(Boolean).join(" ") || inferNameFromIdentifier(identifier),
    role: "member",
    persona: typeof rawPersona === "string" ? (rawPersona as User["persona"]) : undefined,
    onboarded: rawOnboarded === true,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { getToken } = useClerkAuth();
  const { isLoaded, user: clerkUser } = useUser();
  const clerk = useClerk();
  const [user, setResolvedUser] = useState<User | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [syncAttempt, setSyncAttempt] = useState(0);
  const [demoEmail, setDemoEmailState] = useState<string | null>(() =>
    localStorage.getItem(DEMO_EMAIL_STORAGE_KEY),
  );

  const realUserEmail = clerkUser?.primaryEmailAddress?.emailAddress ?? null;
  const isPrivilegedUser = DEMO_PRIVILEGED_EMAILS.has(realUserEmail ?? "");
  const isDemoMode = demoEmail !== null;

  useEffect(() => {
    setAccessTokenProvider(appConfig.useMockApi ? null : async () => (await getToken()) || null);
    return () => setAccessTokenProvider(null);
  }, [getToken]);

  // Keep api-client demo header in sync with state
  useEffect(() => {
    setDemoHeader(demoEmail);
  }, [demoEmail]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!clerkUser) {
      clearStoredSession();
      setAuthError(null);
      setResolvedUser(null);
      return;
    }

    const fallbackUser = mapClerkUser(clerkUser);
    if (appConfig.useMockApi) {
      setAuthError(null);
      setStoredUser(fallbackUser);
      setResolvedUser(fallbackUser);
      return;
    }

    let cancelled = false;
    setAuthError(null);
    setIsSyncing(true);
    refreshSessionUser(fallbackUser.full_name)
      .then((nextUser) => {
        if (!cancelled) {
          setStoredUser(nextUser);
          setAuthError(null);
          setResolvedUser(nextUser);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          clearStoredSession();
          setResolvedUser(null);
          setAuthError(describeAuthSyncError(error));
        }
      })
      .finally(() => {
        if (!cancelled) setIsSyncing(false);
      });

    return () => {
      cancelled = true;
    };
  }, [clerkUser, isLoaded, syncAttempt, demoEmail]);

  const switchDemoUser = (email: string) => {
    localStorage.setItem(DEMO_EMAIL_STORAGE_KEY, email);
    setDemoHeader(email);
    setDemoEmailState(email);
    setSyncAttempt((n) => n + 1);
  };

  const exitDemo = () => {
    localStorage.removeItem(DEMO_EMAIL_STORAGE_KEY);
    setDemoHeader(null);
    setDemoEmailState(null);
    setSyncAttempt((n) => n + 1);
  };

  const setUser = (nextUser: User | null) => {
    if (!nextUser) {
      clearStoredSession();
      setAuthError(null);
      setResolvedUser(null);
      return;
    }
    if (!clerkUser) return;

    setStoredUser(nextUser);
    setAuthError(null);
    setResolvedUser(nextUser);

    void clerkUser.update({
      firstName: nextUser.full_name.split(" ")[0] || undefined,
      lastName: nextUser.full_name.split(" ").slice(1).join(" ") || undefined,
      unsafeMetadata: {
        ...clerkUser.unsafeMetadata,
        onboarded: nextUser.onboarded,
        persona_type: nextUser.persona,
      },
    });
  };

  const logout = () => {
    clearStoredSession();
    setAuthError(null);
    void clerk.signOut({ redirectUrl: "/login" });
  };

  const retrySessionSync = () => {
    if (!isLoaded || !clerkUser || appConfig.useMockApi) return;
    setAuthError(null);
    setSyncAttempt((current) => current + 1);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        retrySessionSync,
        logout,
        isLoading: !isLoaded || isSyncing,
        authError,
        isDemoMode,
        demoEmail,
        isPrivilegedUser,
        switchDemoUser,
        exitDemo,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
