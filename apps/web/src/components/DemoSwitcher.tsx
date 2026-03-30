import { useEffect, useState } from "react";
import { FlaskConical, ChevronDown, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { fetchDemoUsers, type DemoUserEntry } from "@/lib/api";

const ROLE_COLORS: Record<string, string> = {
  admin: "text-red-400",
  coordinator: "text-amber-400",
  member: "text-emerald-400",
};

export default function DemoSwitcher() {
  const { isPrivilegedUser, isDemoMode, demoEmail, switchDemoUser, exitDemo } = useAuth();
  const [demoUsers, setDemoUsers] = useState<DemoUserEntry[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isPrivilegedUser) return;
    setLoading(true);
    fetchDemoUsers()
      .then(setDemoUsers)
      .catch(() => setDemoUsers([]))
      .finally(() => setLoading(false));
  }, [isPrivilegedUser]);

  if (!isPrivilegedUser) return null;

  const currentLabel = demoUsers.find((u) => u.email === demoEmail)?.label ?? demoEmail ?? "Pick a demo user";

  return (
    <div className="relative">
      {isDemoMode && (
        <div className="mx-3 mb-1 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/30 flex items-center justify-between gap-2">
          <span className="text-xs text-amber-400 font-medium truncate">Demo: {currentLabel}</span>
          <button
            onClick={exitDemo}
            className="shrink-0 text-amber-400/70 hover:text-amber-400 transition-colors"
            title="Exit demo mode"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 w-full mx-3 px-3 py-2 rounded-lg text-sm text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground transition-colors"
        style={{ width: "calc(100% - 1.5rem)" }}
      >
        <FlaskConical className="h-4 w-4 shrink-0" />
        <span className="flex-1 text-left truncate">{isDemoMode ? "Switch demo user" : "Demo mode"}</span>
        <ChevronDown className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute bottom-full left-3 right-3 mb-1 z-50 rounded-lg border border-sidebar-border bg-sidebar shadow-lg overflow-hidden">
          <div className="px-3 py-2 border-b border-sidebar-border">
            <p className="text-xs font-semibold text-sidebar-foreground/50 uppercase tracking-wider">View as demo user</p>
          </div>
          {loading ? (
            <div className="px-3 py-3 text-xs text-sidebar-foreground/50">Loading…</div>
          ) : demoUsers.length === 0 ? (
            <div className="px-3 py-3 text-xs text-sidebar-foreground/50">No demo users seeded</div>
          ) : (
            <ul className="py-1 max-h-64 overflow-y-auto">
              {demoUsers.map((u) => (
                <li key={u.email}>
                  <button
                    onClick={() => {
                      switchDemoUser(u.email);
                      setOpen(false);
                    }}
                    className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-sidebar-accent/60 transition-colors text-left ${
                      demoEmail === u.email ? "bg-sidebar-accent/40 text-sidebar-primary" : "text-sidebar-foreground"
                    }`}
                  >
                    <span className="truncate">{u.label}</span>
                    <span className={`text-xs shrink-0 ${ROLE_COLORS[u.role] ?? "text-sidebar-foreground/50"}`}>
                      {u.role}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
