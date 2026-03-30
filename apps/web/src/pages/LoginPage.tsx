import { ClerkLoaded, ClerkLoading, SignIn } from "@clerk/clerk-react";
import { Link } from "react-router-dom";
import AuthShell from "@/components/AuthShell";

export default function LoginPage() {
  return (
    <AuthShell
      title="Welcome back"
      description="Sign in to your care dashboard"
      footer={(
        <p className="text-sm text-center text-muted-foreground mt-6">
          Don't have an account?{" "}
          <Link to="/register" className="text-primary font-medium hover:underline">
            Sign up
          </Link>
        </p>
      )}
    >
      <ClerkLoading>
        <div className="h-[520px] animate-pulse rounded-xl bg-secondary" />
      </ClerkLoading>
      <ClerkLoaded>
        <SignIn path="/login" routing="path" signUpUrl="/register" fallbackRedirectUrl="/dashboard" />
      </ClerkLoaded>
    </AuthShell>
  );
}
