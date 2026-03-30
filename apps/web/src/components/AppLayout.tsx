import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import DemoSwitcher from "@/components/DemoSwitcher";
import {
  LayoutDashboard,
  Activity,
  Users,
  FlaskConical,
  Network,
  UtensilsCrossed,
  ClipboardCheck,
  LogOut,
  Heart,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const memberLinks = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/health", label: "Health", icon: Activity },
  { to: "/recipes", label: "Recipes", icon: UtensilsCrossed },
  { to: "/check-in", label: "Check-in", icon: ClipboardCheck },
];

const coordinatorLinks = [
  { to: "/coordinator", label: "Cases", icon: Users },
];

const adminLinks = [
  { to: "/coordinator", label: "Cases", icon: Users },
  { to: "/scenarios", label: "Scenarios", icon: FlaskConical },
  { to: "/traces", label: "Traces", icon: Network },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const links =
    user?.role === "admin"
      ? adminLinks
      : user?.role === "coordinator"
        ? coordinatorLinks
        : memberLinks;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-sidebar text-sidebar-foreground border-r border-sidebar-border">
        <div className="flex items-center gap-2.5 px-6 py-5 border-b border-sidebar-border">
          <Heart className="h-6 w-6 text-sidebar-primary" />
          <span className="text-lg font-bold text-sidebar-primary-foreground tracking-tight">NüMe</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
                }`
              }
            >
              <link.icon className="h-4.5 w-4.5" />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-4 border-t border-sidebar-border space-y-1">
          <DemoSwitcher />
          <div className="px-3 py-2">
            <p className="text-sm font-medium text-sidebar-accent-foreground truncate">{user?.full_name}</p>
            <p className="text-xs text-sidebar-foreground/60 truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="lg:hidden flex items-center justify-between px-4 py-3 bg-card border-b border-border">
          <div className="flex items-center gap-2">
            <Heart className="h-5 w-5 text-primary" />
            <span className="font-bold tracking-tight">NüMe</span>
          </div>
          <button onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-lg hover:bg-secondary">
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </header>

        {/* Mobile Nav Overlay */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="lg:hidden absolute top-14 inset-x-0 z-50 bg-card border-b border-border shadow-lg"
            >
              <nav className="px-4 py-3 space-y-1">
                {links.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                        isActive ? "bg-accent text-accent-foreground" : "hover:bg-secondary"
                      }`
                    }
                  >
                    <link.icon className="h-4 w-4" />
                    {link.label}
                  </NavLink>
                ))}
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-destructive hover:bg-secondary"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </nav>
            </motion.div>
          )}
        </AnimatePresence>

        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
