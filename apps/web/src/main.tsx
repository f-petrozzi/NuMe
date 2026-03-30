import { ClerkProvider } from "@clerk/clerk-react";
import { createRoot } from "react-dom/client";
import { appConfig } from "@/lib/config";
import App from "./App.tsx";
import "./index.css";

function MissingClerkConfig() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6 text-foreground">
      <div className="max-w-lg rounded-2xl border border-border bg-card p-8 shadow-sm">
        <h1 className="text-2xl font-semibold">Clerk configuration required</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          This app only supports Clerk authentication. Set <code>VITE_CLERK_PUBLISHABLE_KEY</code> and restart the
          frontend.
        </p>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Recommended local command: <code>cd apps/web && doppler run -- npm run dev</code>
        </p>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  appConfig.clerkPublishableKey ? (
    <ClerkProvider
      publishableKey={appConfig.clerkPublishableKey}
      afterSignOutUrl="/login"
      signInFallbackRedirectUrl="/dashboard"
      signUpFallbackRedirectUrl="/onboarding"
    >
      <App />
    </ClerkProvider>
  ) : (
    <MissingClerkConfig />
  ),
);
