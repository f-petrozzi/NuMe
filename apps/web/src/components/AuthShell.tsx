import { Heart } from "lucide-react";
import { motion } from "framer-motion";
import type { ReactNode } from "react";

export default function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:flex lg:w-1/2 bg-sidebar text-sidebar-foreground flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <Heart className="h-8 w-8 text-sidebar-primary" />
          <span className="text-2xl font-bold text-sidebar-primary-foreground tracking-tight">NüMe</span>
        </div>
        <div className="max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-4xl font-bold text-sidebar-primary-foreground leading-tight mb-4"
          >
            Become the new you,
            <br />
            <span className="text-sidebar-primary">with NüMe.</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
            className="text-sidebar-foreground/70 text-lg leading-relaxed"
          >
            NüMe turns sleep, stress, activity, and check-ins into guidance you can actually use.
          </motion.p>
        </div>
        <p className="text-xs text-sidebar-foreground/40">© 2026 NüMe</p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 sm:p-12 bg-background">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-sm"
        >
          <div className="lg:hidden flex items-center gap-2 mb-10">
            <Heart className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold tracking-tight">NüMe</span>
          </div>

          <h2 className="text-2xl font-bold mb-1">{title}</h2>
          <p className="text-muted-foreground mb-8">{description}</p>

          {children}
          {footer}
        </motion.div>
      </div>
    </div>
  );
}
