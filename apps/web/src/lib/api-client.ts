import axios from "axios";

import { appConfig, storageKeys } from "@/lib/config";
import { toast } from "@/hooks/use-toast";
import type { User } from "@/lib/types";

type AccessTokenProvider = (() => Promise<string | null>) | null;

let accessTokenProvider: AccessTokenProvider = null;
let demoAsEmail: string | null = null;

export const apiClient = axios.create({
  baseURL: appConfig.apiBaseUrl,
});

// 429 response interceptor — shows a toast for daily/global limits.
// user_hourly is intentionally omitted here so CheckInPage can show a
// context-specific countdown message instead.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 429) {
      const detail = error.response.data?.detail ?? {};
      const limitType: string = typeof detail === "object" ? (detail.limit_type ?? "") : "";
      const retrySec: number = typeof detail === "object" ? (detail.retry_after_seconds ?? 0) : 0;

      if (limitType === "global_daily") {
        toast({
          title: "Demo capacity reached",
          description: "The demo has hit its daily limit. Check back tomorrow.",
          variant: "destructive",
        });
      } else if (limitType === "user_daily") {
        toast({
          title: "Daily limit reached",
          description: "You've used all your check-ins for today. Resets at midnight UTC.",
          variant: "destructive",
        });
      } else if (limitType === "ip_daily") {
        toast({
          title: "Network limit reached",
          description: "Too many requests from this network today.",
          variant: "destructive",
        });
      } else if (limitType === "ai_disabled") {
        toast({
          title: "AI features paused",
          description: "AI analysis is temporarily disabled. Please check back later.",
          variant: "destructive",
        });
      } else if (limitType !== "user_hourly") {
        // Fallback for unknown limit types (but not user_hourly — let call sites handle that)
        const retryMin = retrySec > 0 ? Math.ceil(retrySec / 60) : null;
        toast({
          title: "Request limited",
          description: retryMin ? `Please try again in ~${retryMin} min.` : "Please try again later.",
          variant: "destructive",
        });
      }
    }
    return Promise.reject(error);
  },
);

apiClient.interceptors.request.use(async (config) => {
  const token = accessTokenProvider ? await accessTokenProvider() : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (demoAsEmail) {
    config.headers["X-Demo-As"] = demoAsEmail;
  }
  return config;
});

export function setAccessTokenProvider(provider: AccessTokenProvider) {
  accessTokenProvider = provider;
}

export function setDemoHeader(email: string | null) {
  demoAsEmail = email;
}

export function getStoredUser(): User | null {
  const stored = localStorage.getItem(storageKeys.user);
  if (!stored) return null;

  try {
    return JSON.parse(stored) as User;
  } catch {
    clearStoredSession();
    return null;
  }
}

export function setStoredUser(user: User) {
  localStorage.setItem(storageKeys.user, JSON.stringify(user));
}

export function clearStoredSession() {
  localStorage.removeItem(storageKeys.user);
}
