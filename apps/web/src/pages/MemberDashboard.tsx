import { useQuery } from "@tanstack/react-query";
import { getDailyQuota, getRecentSignals, getRuns, getSupportPlan } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";
import { UtensilsCrossed, Footprints, Sparkles, TrendingDown, TrendingUp, Moon, Brain, Heart as HeartIcon, Activity, Zap, ZapOff, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { DailyQuotaDto } from "@/lib/api-contracts";
import type { RiskLevel } from "@/lib/types";

const riskConfig: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "Low Risk", className: "bg-success/10 text-success border-success/20" },
  moderate: { label: "Moderate", className: "bg-warning/10 text-warning border-warning/20" },
  high: { label: "High Risk", className: "bg-risk-high/10 text-risk-high border-risk-high/20" },
  critical: { label: "Critical", className: "bg-destructive/10 text-destructive border-destructive/20" },
};

const signalIcons: Record<string, React.ElementType> = {
  sleep_hours: Moon,
  sleep_quality: Moon,
  stress_level: Brain,
  steps: Footprints,
  heart_rate: HeartIcon,
  check_in_mood: Sparkles,
  activity_level: Activity,
};

const cardIcons = [UtensilsCrossed, Activity, Sparkles];
const cardLabels = ["Meal", "Activity", "Wellness"];

function QuotaCard({ quota }: { quota: DailyQuotaDto }) {
  const globalPct = quota.global_units_limit > 0 ? quota.global_units_today / quota.global_units_limit : 0;
  const userRunsUsed = Math.floor(quota.user_units_today / 5); // COST_HEAVY=5
  const userRunsLimit = Math.floor(quota.user_units_limit / 5);
  const resetTime = new Date(quota.reset_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const barColor =
    globalPct >= 0.95 ? "bg-destructive" :
    globalPct >= 0.80 ? "bg-warning" :
    "bg-primary";

  if (!quota.ai_enabled) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="flex items-center gap-3 px-4 py-3 rounded-xl border border-destructive/20 bg-destructive/5"
      >
        <ZapOff className="h-4 w-4 text-destructive shrink-0" />
        <p className="text-sm text-muted-foreground">
          AI analysis is temporarily paused. Check back soon.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 }}
      className="px-4 py-3 rounded-xl border border-border bg-card flex flex-col gap-2.5"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 min-w-0">
          <Zap className="h-3.5 w-3.5 text-primary shrink-0" />
          <div className="flex flex-col min-w-0">
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center gap-1 w-fit cursor-default">
                    <span className="text-xs font-semibold text-foreground leading-none">Global demo capacity</span>
                    <Info className="h-3 w-3 text-muted-foreground/60" />
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-48 text-xs">
                  Shared across all users. Your personal run count is tracked separately.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <span className="text-xs text-muted-foreground">{Math.round(globalPct * 100)}% of daily budget used · resets {resetTime}</span>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <span className="text-xs font-semibold text-foreground leading-none block">Your runs today</span>
          <span className="text-xs text-muted-foreground">{userRunsUsed} of {userRunsLimit} used</span>
        </div>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(globalPct * 100, 100)}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </motion.div>
  );
}

export default function MemberDashboard() {
  const { user } = useAuth();
  const { data: quota } = useQuery({
    queryKey: ["dailyQuota"],
    queryFn: getDailyQuota,
    staleTime: 60_000,
  });
  const { data: runs } = useQuery({
    queryKey: ["runs"],
    queryFn: getRuns,
    refetchInterval: (query) => {
      const latestRun = (query.state.data ?? [])[0];
      return latestRun && (latestRun.status === "pending" || latestRun.status === "running") ? 2000 : false;
    },
  });
  const latestRun = runs?.[0];
  const awaitingLatestPlan = latestRun?.status === "pending" || latestRun?.status === "running";
  const latestRunFailed = latestRun?.status === "failed";
  const { data: plan } = useQuery({
    queryKey: ["supportPlan", latestRun?.id ?? "none", latestRun?.status ?? "idle"],
    queryFn: getSupportPlan,
    refetchInterval: awaitingLatestPlan ? 2000 : false,
  });
  const { data: signals } = useQuery({ queryKey: ["signals"], queryFn: getRecentSignals });

  if (!plan) return <DashboardSkeleton />;

  const displayPlan = awaitingLatestPlan
    ? {
        ...plan,
        empathy_message: "We’re generating your latest support plan now. This dashboard will update automatically when the run completes.",
      }
    : plan;

  const risk = riskConfig[displayPlan.risk_level];
  const interventions = [displayPlan.meal, displayPlan.activity, displayPlan.wellness];
  const confidenceLabel = typeof displayPlan.confidence === "number" ? ` · ${Math.round(displayPlan.confidence * 100)}% confidence` : "";

  return (
    <div className="p-6 lg:p-10 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Good morning, {user?.full_name?.split(" ")[0]}</h1>
          <p className="text-muted-foreground">Here's your personalized NüMe plan for today</p>
        </div>
        <Badge variant="outline" className={`text-sm px-3 py-1 ${risk.className}`}>
          {risk.label}
          {confidenceLabel}
        </Badge>
      </div>

      {/* Quota bar */}
      {quota && <QuotaCard quota={quota} />}

      {/* Empathy Message */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-5 rounded-xl bg-accent border border-primary/10"
      >
        <p className="text-sm leading-relaxed text-accent-foreground">{displayPlan.empathy_message}</p>
      </motion.div>

      {latestRunFailed ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-muted-foreground">
          Your latest run failed before a new plan was produced. This dashboard is still showing the last successful plan.
        </div>
      ) : null}

      {/* Signal Grid */}
      {signals && signals.length > 0 && (() => {
        const byType = signals.reduce<Record<string, typeof signals[0]>>((acc, s) => {
          if (!acc[s.signal_type] || s.recorded_at > acc[s.signal_type].recorded_at) acc[s.signal_type] = s;
          return acc;
        }, {});
        return (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.values(byType).map((s, i) => {
              const Icon = signalIcons[s.signal_type] || Activity;
              const unit = s.unit === "scale_1_10" ? "/10" : s.unit;
              return (
                <motion.div
                  key={s.signal_type}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.04 + i * 0.05 }}
                  className="flex flex-col gap-2 p-3.5 rounded-xl bg-card border border-border hover:border-primary/30 transition-colors"
                >
                  <Icon className="h-3.5 w-3.5 text-primary" />
                  <div className="flex items-baseline gap-1 leading-none">
                    <span className="text-xl font-bold tabular-nums text-foreground">{s.value}</span>
                    <span className="text-xs text-muted-foreground">{unit}</span>
                  </div>
                  <span className="text-xs text-muted-foreground capitalize">{s.signal_type.replace(/_/g, " ")}</span>
                </motion.div>
              );
            })}
          </div>
        );
      })()}

      {/* Intervention Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {interventions.map((item, i) => {
          const Icon = cardIcons[i];
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="p-5 rounded-xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="p-2 rounded-lg bg-accent">
                  <Icon className="h-4 w-4 text-accent-foreground" />
                </div>
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{cardLabels[i]}</span>
                {item.priority === "high" && (
                  <TrendingUp className="h-3.5 w-3.5 text-warning ml-auto" />
                )}
                {item.priority === "low" && (
                  <TrendingDown className="h-3.5 w-3.5 text-success ml-auto" />
                )}
              </div>
              <h3 className="font-semibold text-sm mb-2">{item.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-6 lg:p-10 max-w-5xl mx-auto space-y-8 animate-pulse">
      <div className="h-8 w-64 bg-muted rounded" />
      <div className="h-20 bg-muted rounded-xl" />
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 bg-muted rounded-xl" />
        ))}
      </div>
    </div>
  );
}
