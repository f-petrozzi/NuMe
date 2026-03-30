const DEFAULT_API_URL = "http://localhost:8000";

function parseMockFlag(value: string | undefined): boolean {
  if (!value) return false;
  return value.toLowerCase() === "true";
}

export const appConfig = {
  apiBaseUrl: import.meta.env.VITE_API_URL?.trim() || DEFAULT_API_URL,
  useMockApi: parseMockFlag(import.meta.env.VITE_USE_MOCK_API),
  clerkPublishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY?.trim() || "",
};

export const storageKeys = {
  user: "nume_user",
} as const;
