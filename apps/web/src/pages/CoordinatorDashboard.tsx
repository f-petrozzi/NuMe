import { useQuery } from "@tanstack/react-query";
import { getCases } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { Users, Clock, CheckCircle2, ArrowUpRight } from "lucide-react";
import type { RiskLevel, CaseStatus } from "@/lib/types";

const riskColors: Record<RiskLevel, string> = {
  low: "bg-success/10 text-success",
  moderate: "bg-warning/10 text-warning",
  high: "bg-risk-high/10 text-risk-high",
  critical: "bg-destructive/10 text-destructive",
};

const statusConfig: Record<CaseStatus, { icon: React.ElementType; label: string; className: string }> = {
  open: { icon: Clock, label: "Open", className: "text-info" },
  in_progress: { icon: ArrowUpRight, label: "In Progress", className: "text-warning" },
  closed: { icon: CheckCircle2, label: "Closed", className: "text-success" },
};

export default function CoordinatorDashboard() {
  const { data: cases } = useQuery({ queryKey: ["cases"], queryFn: getCases });

  return (
    <div className="p-6 lg:p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Care Cases</h1>
          <p className="text-muted-foreground">Monitor and manage active care cases</p>
        </div>
      </div>

      {/* Stats */}
      {cases && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {(["open", "in_progress", "closed"] as CaseStatus[]).map((status) => {
            const config = statusConfig[status];
            const count = cases.filter((c) => c.status === status).length;
            return (
              <div key={status} className="p-4 rounded-xl bg-card border border-border shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <config.icon className={`h-4 w-4 ${config.className}`} />
                  <span className="text-xs font-medium text-muted-foreground">{config.label}</span>
                </div>
                <p className="text-2xl font-bold">{count}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Case List */}
      <div className="space-y-3">
        {cases?.map((c, i) => {
          const status = statusConfig[c.status];
          return (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-4 rounded-xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-semibold text-sm">{c.member_label || `Member #${c.user_id}`}</span>
                    {c.persona ? (
                      <Badge variant="outline" className="text-xs capitalize">{c.persona.replace("_", " ")}</Badge>
                    ) : null}
                    <Badge variant="outline" className={`text-xs ${riskColors[c.risk_level]}`}>
                      {c.risk_level} risk
                    </Badge>
                  </div>
                  {c.member_email ? (
                    <p className="text-xs text-muted-foreground mb-1">{c.member_email}</p>
                  ) : null}
                  <p className="text-sm text-muted-foreground line-clamp-2">{c.summary}</p>
                </div>
                <div className={`flex items-center gap-1.5 text-xs font-medium ${status.className}`}>
                  <status.icon className="h-3.5 w-3.5" />
                  {status.label}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
