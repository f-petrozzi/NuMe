import type { ElementType, ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getDailyQuota, getRecentSignals, getRuns, getSupportPlan, logSupportPlanFeedback } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";
import {
  UtensilsCrossed,
  Footprints,
  Sparkles,
  Moon,
  Brain,
  Heart as HeartIcon,
  Activity,
  Zap,
  ZapOff,
  Info,
  ShieldAlert,
  Clock3,
  ArrowRightLeft,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { DailyQuotaDto } from "@/lib/api-contracts";
import type { RiskLevel, SupportPlanAlternative } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";

const riskConfig: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "Low Risk", className: "bg-success/10 text-success border-success/20" },
  moderate: { label: "Moderate", className: "bg-warning/10 text-warning border-warning/20" },
  high: { label: "High Risk", className: "bg-risk-high/10 text-risk-high border-risk-high/20" },
  critical: { label: "Critical", className: "bg-destructive/10 text-destructive border-destructive/20" },
};

const signalIcons: Record<string, ElementType> = {
  sleep_hours: Moon,
  sleep_quality: Moon,
  stress_level: Brain,
  steps: Footprints,
  heart_rate: HeartIcon,
  check_in_mood: Sparkles,
  activity_level: Activity,
};

const cardIcons: Record<"meal" | "activity" | "wellness", ElementType> = {
  meal: UtensilsCrossed,
  activity: Activity,
  wellness: Sparkles,
};
const highlightStateKeys = ["recovery_score", "stress_load", "sleep_debt", "prep_capacity", "routine_stability"];

function formatMetricLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMetricValue(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    if (value >= 0 && value <= 1) return `${Math.round(value * 100)}%`;
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(1);
  }
  return String(value);
}

function formatAlternativeSummary(item: SupportPlanAlternative): string {
  const parts = [item.title];
  if (typeof item.rank === "number") parts.push(`rank ${item.rank}`);
  if (typeof item.score === "number") parts.push(`${Math.round(item.score * 100)} fit`);
  return parts.join(" · ");
}

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
  const { toast } = useToast();
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
  const feedbackMutation = useMutation({
    mutationFn: logSupportPlanFeedback,
  });

  if (!plan) return <DashboardSkeleton />;

  const currentPlan = plan.plan;
  const empathyMessage = awaitingLatestPlan
    ? "We’re generating your latest support plan now. This dashboard will update automatically when the run completes."
    : currentPlan?.empathy_message || plan.risk.rationale || "Your support plan will appear here after the first completed run.";
  const risk = riskConfig[plan.risk.level];
  const confidenceLabel = plan.risk.confidence > 0 ? ` · ${Math.round(plan.risk.confidence * 100)}% confidence` : "";
  const snapshotHighlights = highlightStateKeys
    .map((key) => [key, plan.state_snapshot?.dynamic_state?.[key]] as const)
    .filter((entry) => typeof entry[1] === "number");
  const riskSubscores = Object.entries(plan.risk.subscores).sort((a, b) => b[1] - a[1]);

  function submitRecommendationFeedback(
    recommendationKind: "meal" | "activity" | "wellness",
    eventType: "accepted" | "skipped",
    recommendationId: string | undefined,
    recommendationTitle: string,
  ) {
    if (!currentPlan) return;
    feedbackMutation.mutate(
      {
        intervention_id: currentPlan.intervention_id,
        run_id: plan.run?.id,
        event_type: eventType,
        source: "member_dashboard",
        recommendation_kind: recommendationKind,
        recommendation_id: recommendationId,
        payload: {
          recommendation_title: recommendationTitle,
          support_plan_generated_at: plan.generated_at,
        },
      },
      {
        onSuccess: () => {
          toast({
            title: "Feedback saved",
            description: `${recommendationTitle} marked ${eventType}.`,
          });
        },
        onError: () => {
          toast({
            title: "Couldn't save feedback",
            description: "Try again in a moment.",
            variant: "destructive",
          });
        },
      },
    );
  }

  return (
    <div className="p-6 lg:p-10 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Good morning, {user?.full_name?.split(" ")[0]}</h1>
          <p className="text-muted-foreground">
            {currentPlan
              ? `Here's your structured NüMe plan for today${plan.generated_at ? ` · updated ${new Date(plan.generated_at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}` : ""}`
              : "Run a scenario or submit a check-in to generate your structured support plan."}
          </p>
        </div>
        <Badge variant="outline" className={`text-sm px-3 py-1 ${risk.className}`}>
          {risk.label}
          {confidenceLabel}
        </Badge>
      </div>

      {/* Quota bar */}
      {quota && <QuotaCard quota={quota} />}

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-5 rounded-xl bg-accent border border-primary/10"
      >
        <p className="text-sm leading-relaxed text-accent-foreground">{empathyMessage}</p>
      </motion.div>

      {awaitingLatestPlan && currentPlan ? (
        <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground">
          A newer run is still in progress. This dashboard is showing the most recent completed structured support plan until the new run finishes.
        </div>
      ) : null}

      {latestRunFailed ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-muted-foreground">
          Your latest run failed before a new plan was produced. This dashboard is still showing the last successful plan.
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-accent p-2">
              <ShieldAlert className="h-4 w-4 text-accent-foreground" />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Risk Drivers</h2>
              <p className="text-sm text-foreground">{plan.risk.rationale || "Risk details will appear here after the first completed plan."}</p>
            </div>
          </div>

          {plan.risk.drivers.length > 0 ? (
            <div className="space-y-2">
              {plan.risk.drivers.map((driver) => (
                <div key={driver} className="rounded-lg border border-border/70 bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                  {driver}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No strong drivers are available yet for the current support-plan snapshot.</p>
          )}

          {riskSubscores.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {riskSubscores.slice(0, 4).map(([key, value]) => (
                <Badge key={key} variant="secondary" className="text-xs">
                  {formatMetricLabel(key)} {Math.round(value * 100)}%
                </Badge>
              ))}
            </div>
          ) : null}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-accent p-2">
              <Clock3 className="h-4 w-4 text-accent-foreground" />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Current State Snapshot</h2>
              <p className="text-sm text-foreground">
                {plan.state_snapshot
                  ? `Source: ${formatMetricLabel(plan.state_snapshot.source)}`
                  : "A linked personalization snapshot will appear here once a structured plan is available."}
              </p>
            </div>
          </div>

          {snapshotHighlights.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              {snapshotHighlights.map(([key, value]) => (
                <div key={key} className="rounded-lg border border-border/70 bg-muted/20 p-3">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">{formatMetricLabel(key)}</p>
                  <p className="mt-1 text-lg font-semibold">{formatMetricValue(value)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Snapshot metrics will populate after the first completed structured plan.</p>
          )}

          {currentPlan?.why_changed_from_previous?.length ? (
            <div className="mt-4 rounded-lg border border-border/70 bg-muted/20 p-3">
              <div className="mb-2 flex items-center gap-2">
                <ArrowRightLeft className="h-3.5 w-3.5 text-primary" />
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">What Changed</p>
              </div>
              <div className="space-y-1.5">
                {currentPlan.why_changed_from_previous.map((reason) => (
                  <p key={reason} className="text-sm text-muted-foreground">
                    {reason}
                  </p>
                ))}
              </div>
            </div>
          ) : null}
        </motion.div>
      </div>

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

      {currentPlan ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SupportPlanCard
            label="Meal"
            icon={cardIcons.meal}
            title={currentPlan.meal.title}
            description={currentPlan.meal.text || currentPlan.meal.description}
            reasons={currentPlan.meal.why_chosen}
            alternatives={currentPlan.meal.alternatives_considered}
            meta={[
              currentPlan.meal.recipe ? `${currentPlan.meal.recipe.prep_time + currentPlan.meal.recipe.cook_time} min total` : "",
              currentPlan.meal.recipe?.protein_grams != null ? `${currentPlan.meal.recipe.protein_grams}g protein` : "",
              currentPlan.meal.recipe?.prep_effort ? `${currentPlan.meal.recipe.prep_effort} effort` : "",
            ].filter(Boolean)}
            actions={
              <RecommendationFeedbackActions
                label="meal"
                busy={feedbackMutation.isPending}
                onAccept={() => submitRecommendationFeedback("meal", "accepted", currentPlan.meal.recipe_id, currentPlan.meal.title)}
                onSkip={() => submitRecommendationFeedback("meal", "skipped", currentPlan.meal.recipe_id, currentPlan.meal.title)}
              />
            }
          >
            {currentPlan.meal.recipe ? (
              <div className="rounded-lg border border-primary/10 bg-primary/5 p-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recipe Fit</p>
                <p className="mt-1 font-medium">{currentPlan.meal.recipe.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{currentPlan.meal.recipe.description}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {currentPlan.meal.constraints.map((constraint) => (
                    <Badge key={constraint} variant="secondary" className="text-[11px]">
                      {constraint.replace(/_/g, " ")}
                    </Badge>
                  ))}
                  {currentPlan.meal.recipe.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="outline" className="text-[11px]">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
          </SupportPlanCard>

          <SupportPlanCard
            label="Activity"
            icon={cardIcons.activity}
            title={currentPlan.activity.title}
            description={currentPlan.activity.text || currentPlan.activity.description}
            reasons={currentPlan.activity.why_chosen}
            alternatives={currentPlan.activity.alternatives_considered}
            meta={[
              currentPlan.activity.duration_minutes ? `${currentPlan.activity.duration_minutes} min` : "",
              currentPlan.activity.intensity ? `${currentPlan.activity.intensity} intensity` : "",
              currentPlan.activity.template?.time_cost_level ? `${currentPlan.activity.template.time_cost_level} time cost` : "",
            ].filter(Boolean)}
            actions={
              <RecommendationFeedbackActions
                label="activity"
                busy={feedbackMutation.isPending}
                onAccept={() => submitRecommendationFeedback("activity", "accepted", currentPlan.activity.template_id, currentPlan.activity.title)}
                onSkip={() => submitRecommendationFeedback("activity", "skipped", currentPlan.activity.template_id, currentPlan.activity.title)}
              />
            }
          />

          <SupportPlanCard
            label="Wellness"
            icon={cardIcons.wellness}
            title={currentPlan.wellness.title}
            description={currentPlan.wellness.text || currentPlan.wellness.description}
            reasons={currentPlan.wellness.why_chosen}
            alternatives={currentPlan.wellness.alternatives_considered}
            meta={[
              currentPlan.wellness.category ? currentPlan.wellness.category : "",
              currentPlan.wellness.template?.duration_minutes ? `${currentPlan.wellness.template.duration_minutes} min` : "",
              currentPlan.wellness.template?.time_cost_level ? `${currentPlan.wellness.template.time_cost_level} time cost` : "",
            ].filter(Boolean)}
            actions={
              <RecommendationFeedbackActions
                label="wellness"
                busy={feedbackMutation.isPending}
                onAccept={() => submitRecommendationFeedback("wellness", "accepted", currentPlan.wellness.template_id, currentPlan.wellness.title)}
                onSkip={() => submitRecommendationFeedback("wellness", "skipped", currentPlan.wellness.template_id, currentPlan.wellness.title)}
              />
            }
          />
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border bg-muted/30 p-6">
          <p className="font-semibold">No structured support plan yet</p>
          <p className="mt-2 text-sm text-muted-foreground">
            {awaitingLatestPlan
              ? "A run is in progress now. This dashboard will populate automatically when the structured support plan is ready."
              : "Run a scenario or submit a check-in to generate a structured support plan with risk drivers, linked recommendations, and change reasons."}
          </p>
        </div>
      )}
    </div>
  );
}

function SupportPlanCard({
  label,
  icon: Icon,
  title,
  description,
  reasons,
  alternatives,
  meta,
  children,
  actions,
}: {
  label: string;
  icon: ElementType;
  title: string;
  description: string;
  reasons: string[];
  alternatives: SupportPlanAlternative[];
  meta: string[];
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-5 rounded-xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="mb-3 flex items-center gap-2">
        <div className="rounded-lg bg-accent p-2">
          <Icon className="h-4 w-4 text-accent-foreground" />
        </div>
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
      </div>

      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>

      {meta.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {meta.map((item) => (
            <Badge key={item} variant="outline" className="text-[11px]">
              {item}
            </Badge>
          ))}
        </div>
      ) : null}

      {reasons.length > 0 ? (
        <div className="mt-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Why Chosen</p>
          {reasons.slice(0, 3).map((reason) => (
            <p key={reason} className="text-sm text-muted-foreground">
              {reason}
            </p>
          ))}
        </div>
      ) : null}

      {children ? <div className="mt-4">{children}</div> : null}
      {actions ? <div className="mt-4">{actions}</div> : null}

      {alternatives.length > 0 ? (
        <div className="mt-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Alternatives Considered</p>
          {alternatives.slice(0, 2).map((item) => (
            <p key={`${item.kind}-${item.reference_id || item.title}`} className="text-sm text-muted-foreground">
              {formatAlternativeSummary(item)}
            </p>
          ))}
        </div>
      ) : null}
    </motion.div>
  );
}

function RecommendationFeedbackActions({
  label,
  busy,
  onAccept,
  onSkip,
}: {
  label: string;
  busy: boolean;
  onAccept: () => void;
  onSkip: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        size="sm"
        onClick={onAccept}
        disabled={busy}
        aria-label={`Accept ${label} recommendation`}
      >
        I'll do this
      </Button>
      <Button
        size="sm"
        variant="outline"
        onClick={onSkip}
        disabled={busy}
        aria-label={`Skip ${label} recommendation`}
      >
        Not today
      </Button>
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
