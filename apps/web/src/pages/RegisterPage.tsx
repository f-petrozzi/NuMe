import { ClerkLoaded, ClerkLoading, SignUp } from "@clerk/clerk-react";
import { Link } from "react-router-dom";
import AuthShell from "@/components/AuthShell";

export default function RegisterPage() {
  return (
    <AuthShell
      title="Create your account"
      description="Start your personalized care journey"
      footer={(
        <p className="text-sm text-center text-muted-foreground mt-6">
          Already have an account? <Link to="/login" className="text-primary font-medium hover:underline">Sign in</Link>
        </p>
      )}
    >
      <ClerkLoading>
        <div className="h-[560px] animate-pulse rounded-xl bg-secondary" />
      </ClerkLoading>
      <ClerkLoaded>
        <SignUp path="/register" routing="path" signInUrl="/login" fallbackRedirectUrl="/onboarding" />
      </ClerkLoaded>
    </AuthShell>
  );
}
