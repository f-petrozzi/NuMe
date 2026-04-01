import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getDailyQuota, submitCheckIn } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { ClipboardCheck, Loader2, ArrowRight, Frown, Meh, Smile, ZapOff, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function CheckInPage() {
  const [mood, setMood] = useState(5);
  const [sleep, setSleep] = useState(7);
  const [stress, setStress] = useState(30);
  const [note, setNote] = useState("");
  const [hourlyError, setHourlyError] = useState<string | null>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: quota } = useQuery({
    queryKey: ["dailyQuota"],
    queryFn: getDailyQuota,
    staleTime: 60_000,
  });

  const userRunsUsed = quota ? Math.floor(quota.user_units_today / 5) : 0;
  const userRunsLimit = quota ? Math.floor(quota.user_units_limit / 5) : 10;
  const atDailyLimit = quota ? quota.user_units_today >= quota.user_units_limit : false;
  const aiDisabled = quota ? !quota.ai_enabled : false;
  const isBlocked = atDailyLimit || aiDisabled;

  const submit = useMutation({
    mutationFn: submitCheckIn,
    onSuccess: async () => {
      setHourlyError(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["runs"] }),
        qc.invalidateQueries({ queryKey: ["supportPlan"] }),
        qc.invalidateQueries({ queryKey: ["signals"] }),
        qc.invalidateQueries({ queryKey: ["dailyQuota"] }),
      ]);
      navigate("/dashboard");
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      if (typeof detail === "object" && detail !== null) {
        const d = detail as Record<string, unknown>;
        if (d.limit_type === "user_hourly") {
          const secs = typeof d.retry_after_seconds === "number" ? d.retry_after_seconds : 0;
          const mins = Math.ceil(secs / 60);
          setHourlyError(`You've reached your hourly limit. Try again in ~${mins} min.`);
          return;
        }
      }
      // Other errors handled by the global 429 interceptor in api-client.ts
    },
  });

  const moodStates = [
    { icon: Frown, label: "Very low" },
    { icon: Frown, label: "Low" },
    { icon: Meh, label: "Okay" },
    { icon: Smile, label: "Good" },
    { icon: Smile, label: "Great" },
  ] as const;
  const moodState = moodStates[Math.min(Math.floor(mood / 2.5), 4)];
  const MoodIcon = moodState.icon;

  return (
    <div className="p-6 lg:p-10 max-w-lg mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <ClipboardCheck className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Check-in</h1>
          <p className="text-muted-foreground">How are you feeling today?</p>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <div className="space-y-3">
          <Label className="flex items-center gap-2 text-sm font-semibold">
            <MoodIcon className="h-4 w-4 text-primary" />
            Mood: {moodState.label}
          </Label>
          <Slider value={[mood]} onValueChange={([v]) => setMood(v)} min={1} max={10} step={1} />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Very low</span><span>Great</span>
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-sm font-semibold">Sleep: {sleep}h</Label>
          <Slider value={[sleep]} onValueChange={([v]) => setSleep(v)} min={0} max={12} step={0.5} />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0h</span><span>12h</span>
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-sm font-semibold">Stress level: {stress}%</Label>
          <Slider value={[stress]} onValueChange={([v]) => setStress(v)} min={0} max={100} step={5} />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Calm</span><span>Very stressed</span>
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-semibold">Notes (optional)</Label>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Anything you'd like to share about your day…"
            rows={3}
          />
        </div>

        {aiDisabled && (
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-muted-foreground">
            <ZapOff className="h-4 w-4 text-destructive shrink-0" />
            AI analysis is temporarily paused. Check back soon.
          </div>
        )}

        {!aiDisabled && atDailyLimit && (
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-warning/20 bg-warning/5 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4 text-warning shrink-0" />
            You've used all {userRunsLimit} check-ins for today. Resets at midnight UTC.
          </div>
        )}

        {hourlyError && (
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-warning/20 bg-warning/5 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4 text-warning shrink-0" />
            {hourlyError}
          </div>
        )}

        {quota && !isBlocked && (
          <p className="text-xs text-muted-foreground text-center">
            {userRunsUsed}/{userRunsLimit} check-ins used today
          </p>
        )}

        <Button
          onClick={() => { setHourlyError(null); submit.mutate({ mood, sleep_hours: sleep, stress, note }); }}
          disabled={submit.isPending || isBlocked}
          className="w-full"
          size="lg"
        >
          {submit.isPending ? (
            <><Loader2 className="h-4 w-4 animate-spin mr-2" />Analyzing…</>
          ) : (
            <>Submit check-in <ArrowRight className="h-4 w-4 ml-2" /></>
          )}
        </Button>
      </motion.div>
    </div>
  );
}
