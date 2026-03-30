import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addCalorieLog,
  connectGarmin,
  deleteCalorieLog,
  disconnectGarmin,
  estimateCalories,
  getActivities,
  getCalorieLog,
  getDailyMetrics,
  getGarminAuthStatus,
  getHealthSummary,
  getSleepHistory,
  triggerGarminSync,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  Activity,
  Brain,
  CheckCircle2,
  ChevronRight,
  Flame,
  Footprints,
  HeartPulse,
  Moon,
  Plus,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Unlink,
  Wifi,
  WifiOff,
  X,
  Zap,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import type { CalorieLogDto } from "@/lib/api-contracts";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function fmtDistance(meters: number): string {
  if (meters === 0) return "—";
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${meters} m`;
}

function fmtDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function fmtDateTime(isoStr: string): string {
  return new Date(isoStr).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function sleepQuality(score: number): { label: string; color: string } {
  if (score >= 85) return { label: "Excellent", color: "text-green-500" };
  if (score >= 70) return { label: "Good", color: "text-emerald-500" };
  if (score >= 55) return { label: "Fair", color: "text-yellow-500" };
  return { label: "Poor", color: "text-red-500" };
}

const ACTIVITY_ICONS: Record<string, string> = {
  running: "🏃", cycling: "🚴", walking: "🚶", swimming: "🏊",
  strength_training: "🏋️", yoga: "🧘", hiking: "🥾", elliptical: "⚙️",
};

// ---------------------------------------------------------------------------
// Garmin connection panel
// ---------------------------------------------------------------------------

function GarminPanel() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const { data: status, isLoading } = useQuery({
    queryKey: ["garmin-status"],
    queryFn: getGarminAuthStatus,
  });

  const connectMut = useMutation({
    mutationFn: ({ e, p }: { e: string; p: string }) => connectGarmin(e, p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["garmin-status"] });
      qc.invalidateQueries({ queryKey: ["health"] });
      setDialogOpen(false);
      setEmail("");
      setPassword("");
      toast({ title: "Garmin connected", description: "Your account is linked and data will sync shortly." });
    },
    onError: (err: Error) => {
      toast({ title: "Connection failed", description: err.message, variant: "destructive" });
    },
  });

  const disconnectMut = useMutation({
    mutationFn: disconnectGarmin,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["garmin-status"] });
      qc.invalidateQueries({ queryKey: ["health"] });
      toast({ title: "Garmin disconnected" });
    },
  });

  const syncMut = useMutation({
    mutationFn: triggerGarminSync,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["health"] });
      qc.invalidateQueries({ queryKey: ["daily-metrics"] });
      qc.invalidateQueries({ queryKey: ["sleep-history"] });
      qc.invalidateQueries({ queryKey: ["activities"] });
      toast({ title: "Sync complete", description: `${result.synced ?? "—"} days updated.` });
    },
    onError: (err: Error) => {
      toast({ title: "Sync failed", description: err.message, variant: "destructive" });
    },
  });

  if (isLoading) {
    return <div className="h-16 rounded-xl bg-muted animate-pulse" />;
  }

  const connected = status?.connected ?? false;

  return (
    <>
      <div className={`flex items-center justify-between px-4 py-3 rounded-xl border ${connected ? "border-green-500/30 bg-green-500/5" : "border-border bg-muted/40"}`}>
        <div className="flex items-center gap-3">
          {connected ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-muted-foreground" />
          )}
          <div>
            <p className="text-sm font-medium">
              {connected ? `Garmin connected${status?.garmin_email ? ` — ${status.garmin_email}` : ""}` : "Garmin not connected"}
            </p>
            {connected && status?.last_sync && (
              <p className="text-xs text-muted-foreground">Last sync: {fmtDateTime(status.last_sync)}</p>
            )}
            {!connected && (
              <p className="text-xs text-muted-foreground">Connect to sync wearable data automatically</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {connected && (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => syncMut.mutate()}
                disabled={syncMut.isPending}
              >
                <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${syncMut.isPending ? "animate-spin" : ""}`} />
                {syncMut.isPending ? "Syncing…" : "Sync now"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="text-muted-foreground hover:text-destructive"
                onClick={() => disconnectMut.mutate()}
                disabled={disconnectMut.isPending}
              >
                <Unlink className="h-3.5 w-3.5 mr-1" />
                Disconnect
              </Button>
            </>
          )}
          {!connected && (
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              Connect Garmin
            </Button>
          )}
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Connect Garmin account</DialogTitle>
            <DialogDescription>
              Enter your Garmin Connect credentials. They are sent directly to the backend and are not stored in the browser.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="garmin-email">Garmin email</Label>
              <Input
                id="garmin-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="garmin-password">Password</Label>
              <Input
                id="garmin-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            <Button
              className="w-full"
              disabled={!email || !password || connectMut.isPending}
              onClick={() => connectMut.mutate({ e: email, p: password })}
            >
              {connectMut.isPending ? "Connecting…" : "Connect"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ---------------------------------------------------------------------------
// Overview tab
// ---------------------------------------------------------------------------

function OverviewTab() {
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: getHealthSummary });

  if (!health) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => <div key={i} className="h-40 bg-muted rounded-xl" />)}
      </div>
    );
  }

  const cards = [
    {
      label: "Steps",
      value: health.steps.current.toLocaleString(),
      sub: `Goal: ${health.steps.goal.toLocaleString()}`,
      trend: health.steps.trend,
      icon: Footprints,
      progress: (health.steps.current / health.steps.goal) * 100,
    },
    {
      label: "Sleep",
      value: `${health.sleep.hours}h`,
      sub: health.sleep.quality,
      trend: health.sleep.trend,
      icon: Moon,
      progress: (health.sleep.hours / 8) * 100,
    },
    {
      label: "Heart Rate",
      value: `${health.heart_rate.current} bpm`,
      sub: `Resting: ${health.heart_rate.resting} bpm`,
      trend: health.heart_rate.trend,
      icon: HeartPulse,
      progress: null,
    },
    {
      label: "Stress",
      value: `${health.stress.level}/100`,
      sub: health.stress.level > 60 ? "Elevated" : "Normal",
      trend: health.stress.trend,
      icon: Brain,
      progress: health.stress.level,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.07 }}
          className="p-5 rounded-xl bg-card border border-border shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-accent">
                <card.icon className="h-4 w-4 text-accent-foreground" />
              </div>
              <span className="text-sm font-medium text-muted-foreground">{card.label}</span>
            </div>
            {card.trend !== 0 && (
              <div className={`flex items-center gap-1 text-xs font-medium ${card.trend > 0 ? (card.label === "Stress" || card.label === "Heart Rate" ? "text-yellow-500" : "text-green-500") : (card.label === "Stress" ? "text-green-500" : "text-yellow-500")}`}>
                {card.trend > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {Math.abs(card.trend)}%
              </div>
            )}
          </div>
          <p className="text-2xl font-bold mb-1">{card.value}</p>
          <p className="text-sm text-muted-foreground mb-3">{card.sub}</p>
          {card.progress !== null && (
            <Progress value={Math.min(card.progress, 100)} className="h-1.5" />
          )}
        </motion.div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trends tab
// ---------------------------------------------------------------------------

type TrendMetric = "steps" | "stress_avg" | "avg_hr" | "active_calories";

const TREND_OPTIONS: { value: TrendMetric; label: string; color: string }[] = [
  { value: "steps", label: "Steps", color: "#6366f1" },
  { value: "stress_avg", label: "Stress", color: "#f97316" },
  { value: "avg_hr", label: "Avg HR", color: "#ef4444" },
  { value: "active_calories", label: "Active Cal", color: "#10b981" },
];

function TrendsTab() {
  const [metric, setMetric] = useState<TrendMetric>("steps");
  const { data: daily = [], isLoading } = useQuery({
    queryKey: ["daily-metrics"],
    queryFn: () => getDailyMetrics(30),
  });

  const selected = TREND_OPTIONS.find((o) => o.value === metric)!;

  const chartData = [...daily]
    .sort((a, b) => a.metric_date.localeCompare(b.metric_date))
    .map((d) => ({
      date: fmtDate(d.metric_date),
      value: d[metric] as number,
    }));

  if (isLoading) {
    return <div className="h-64 bg-muted animate-pulse rounded-xl" />;
  }

  if (!daily.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <Zap className="h-8 w-8 mb-3 opacity-40" />
        <p className="text-sm">No trend data yet — connect Garmin and sync to see history.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {TREND_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setMetric(opt.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${metric === opt.value ? "bg-foreground text-background border-foreground" : "border-border text-muted-foreground hover:border-foreground/50"}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="rounded-xl border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground mb-4">{selected.label} — last 30 days</p>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "hsl(var(--foreground))" }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={selected.color}
              strokeWidth={2}
              dot={{ r: 3, fill: selected.color }}
              activeDot={{ r: 5 }}
              name={selected.label}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sleep tab
// ---------------------------------------------------------------------------

function SleepTab() {
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["sleep-history"],
    queryFn: () => getSleepHistory(30),
  });

  if (isLoading) {
    return <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-20 bg-muted animate-pulse rounded-xl"/>)}</div>;
  }

  if (!sessions.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <Moon className="h-8 w-8 mb-3 opacity-40" />
        <p className="text-sm">No sleep data yet — connect Garmin to see your sleep history.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sessions.map((s) => {
        const totalSec = s.deep_seconds + s.light_seconds + s.rem_seconds + s.awake_seconds || 1;
        const q = sleepQuality(s.sleep_score);
        const hrs = (s.duration_seconds / 3600).toFixed(1);
        return (
          <motion.div
            key={s.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl border border-border bg-card"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-medium text-sm">{fmtDate(s.sleep_date)}</p>
                <p className="text-xs text-muted-foreground">{hrs}h · Score: {s.sleep_score}</p>
              </div>
              <Badge variant="outline" className={q.color}>{q.label}</Badge>
            </div>
            <div className="flex gap-1 h-2 rounded-full overflow-hidden">
              <div className="bg-indigo-500" style={{ width: `${(s.deep_seconds / totalSec) * 100}%` }} title="Deep" />
              <div className="bg-blue-400" style={{ width: `${(s.light_seconds / totalSec) * 100}%` }} title="Light" />
              <div className="bg-violet-400" style={{ width: `${(s.rem_seconds / totalSec) * 100}%` }} title="REM" />
              <div className="bg-muted" style={{ width: `${(s.awake_seconds / totalSec) * 100}%` }} title="Awake" />
            </div>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              <span><span className="inline-block w-2 h-2 rounded-full bg-indigo-500 mr-1" />Deep {fmtDuration(s.deep_seconds)}</span>
              <span><span className="inline-block w-2 h-2 rounded-full bg-blue-400 mr-1" />Light {fmtDuration(s.light_seconds)}</span>
              <span><span className="inline-block w-2 h-2 rounded-full bg-violet-400 mr-1" />REM {fmtDuration(s.rem_seconds)}</span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Activity tab
// ---------------------------------------------------------------------------

function ActivityTab() {
  const { data: activities = [], isLoading } = useQuery({
    queryKey: ["activities"],
    queryFn: () => getActivities(20),
  });

  if (isLoading) {
    return <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-20 bg-muted animate-pulse rounded-xl"/>)}</div>;
  }

  if (!activities.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <Activity className="h-8 w-8 mb-3 opacity-40" />
        <p className="text-sm">No activities yet — connect Garmin to import your workouts.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {activities.map((a, i) => {
        const emoji = ACTIVITY_ICONS[a.activity_type] ?? "🏃";
        return (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="flex items-center gap-4 p-4 rounded-xl border border-border bg-card"
          >
            <span className="text-2xl">{emoji}</span>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm capitalize">{a.activity_name}</p>
              <p className="text-xs text-muted-foreground">{fmtDateTime(a.start_time)}</p>
            </div>
            <div className="text-right text-xs text-muted-foreground space-y-0.5">
              <p>{fmtDuration(a.duration_seconds)}</p>
              {a.distance_meters > 0 && <p>{fmtDistance(a.distance_meters)}</p>}
              {a.calories > 0 && <p className="text-orange-500 font-medium">{a.calories} kcal</p>}
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground/40 shrink-0" />
          </motion.div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Calorie log tab
// ---------------------------------------------------------------------------

const MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack", "other"];
const TODAY = new Date().toISOString().slice(0, 10);

function CalorieTab() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [foodName, setFoodName] = useState("");
  const [quantity, setQuantity] = useState("1 serving");
  const [mealType, setMealType] = useState("lunch");
  const [manualCals, setManualCals] = useState("");
  const [estimate, setEstimate] = useState<{ calories: number; confidence: string } | null>(null);

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["calorie-log", TODAY],
    queryFn: () => getCalorieLog(TODAY),
  });

  const estimateMut = useMutation({
    mutationFn: () => estimateCalories(foodName, quantity),
    onSuccess: (res) => {
      setEstimate({ calories: res.estimated_calories, confidence: res.confidence });
      setManualCals(String(res.estimated_calories));
    },
    onError: () => toast({ title: "Estimate failed", variant: "destructive" }),
  });

  const addMut = useMutation({
    mutationFn: () =>
      addCalorieLog({
        log_date: TODAY,
        meal_type: mealType,
        food_name: foodName,
        calories: Number(manualCals) || 0,
        quantity,
        notes: "",
        ai_estimated: estimate !== null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["calorie-log"] });
      setFoodName("");
      setQuantity("1 serving");
      setManualCals("");
      setEstimate(null);
      toast({ title: "Entry added" });
    },
    onError: () => toast({ title: "Failed to add entry", variant: "destructive" }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteCalorieLog(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calorie-log"] }),
  });

  const totalCalories = entries.reduce((sum, e) => sum + e.calories, 0);

  const byMeal = MEAL_TYPES.reduce<Record<string, CalorieLogDto[]>>((acc, m) => {
    acc[m] = entries.filter((e) => e.meal_type === m);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-card">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-orange-500/10">
            <Flame className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Today's total</p>
            <p className="text-2xl font-bold">{totalCalories.toLocaleString()} kcal</p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{entries.length} {entries.length === 1 ? "entry" : "entries"}</p>
      </div>

      {/* Add entry form */}
      <div className="p-4 rounded-xl border border-border bg-card space-y-4">
        <p className="text-sm font-semibold flex items-center gap-2">
          <Plus className="h-4 w-4" /> Log food
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 space-y-1">
            <Label htmlFor="food-name">Food / drink</Label>
            <Input
              id="food-name"
              value={foodName}
              onChange={(e) => { setFoodName(e.target.value); setEstimate(null); }}
              placeholder="e.g. Oatmeal with banana"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="quantity">Quantity</Label>
            <Input id="quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="1 serving" />
          </div>
          <div className="space-y-1">
            <Label>Meal</Label>
            <Select value={mealType} onValueChange={setMealType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MEAL_TYPES.map((m) => (
                  <SelectItem key={m} value={m} className="capitalize">{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex items-end gap-3">
          <div className="flex-1 space-y-1">
            <Label htmlFor="calories">Calories</Label>
            <Input
              id="calories"
              type="number"
              min={0}
              value={manualCals}
              onChange={(e) => setManualCals(e.target.value)}
              placeholder="kcal"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={!foodName || estimateMut.isPending}
            onClick={() => estimateMut.mutate()}
            className="shrink-0"
          >
            <Sparkles className={`h-3.5 w-3.5 mr-1.5 ${estimateMut.isPending ? "animate-pulse" : ""}`} />
            {estimateMut.isPending ? "Estimating…" : "AI estimate"}
          </Button>
        </div>

        {estimate && (
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
            AI estimated {estimate.calories} kcal ({estimate.confidence} confidence)
          </p>
        )}

        <Button
          className="w-full"
          disabled={!foodName || !manualCals || addMut.isPending}
          onClick={() => addMut.mutate()}
        >
          {addMut.isPending ? "Adding…" : "Add entry"}
        </Button>
      </div>

      {/* Log entries grouped by meal */}
      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map(i=><div key={i} className="h-12 bg-muted animate-pulse rounded-lg"/>)}</div>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-6">No entries for today yet.</p>
      ) : (
        <div className="space-y-4">
          {MEAL_TYPES.filter((m) => byMeal[m].length > 0).map((meal) => (
            <div key={meal}>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 capitalize">{meal}</p>
              <div className="space-y-2">
                {byMeal[meal].map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between px-3 py-2 rounded-lg border border-border bg-card/50 text-sm">
                    <div className="flex items-center gap-2 min-w-0">
                      {entry.ai_estimated && <Sparkles className="h-3 w-3 text-violet-400 shrink-0" />}
                      <span className="truncate">{entry.food_name}</span>
                      <span className="text-muted-foreground text-xs shrink-0">{entry.quantity}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="font-medium text-orange-500">{entry.calories} kcal</span>
                      <button
                        onClick={() => deleteMut.mutate(entry.id)}
                        disabled={deleteMut.isPending}
                        className="text-muted-foreground/40 hover:text-destructive transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function HealthDashboard() {
  return (
    <div className="p-6 lg:p-10 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Health</h1>
        <p className="text-muted-foreground text-sm">Wearable data, trends, and nutrition tracking</p>
      </div>

      <GarminPanel />

      <Tabs defaultValue="overview">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="sleep">Sleep</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="calories">Calories</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab />
        </TabsContent>
        <TabsContent value="trends" className="mt-6">
          <TrendsTab />
        </TabsContent>
        <TabsContent value="sleep" className="mt-6">
          <SleepTab />
        </TabsContent>
        <TabsContent value="activity" className="mt-6">
          <ActivityTab />
        </TabsContent>
        <TabsContent value="calories" className="mt-6">
          <CalorieTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
