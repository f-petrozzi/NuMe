import axios from "axios";

import { appConfig, storageKeys } from "@/lib/config";
import type { User } from "@/lib/types";

type AccessTokenProvider = (() => Promise<string | null>) | null;

let accessTokenProvider: AccessTokenProvider = null;
let demoAsEmail: string | null = null;

export const apiClient = axios.create({
  baseURL: appConfig.apiBaseUrl,
});

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
