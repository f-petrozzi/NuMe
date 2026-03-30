import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitCheckIn } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { ClipboardCheck, Loader2, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

export default function CheckInPage() {
  const [mood, setMood] = useState(5);
  const [sleep, setSleep] = useState(7);
  const [stress, setStress] = useState(30);
  const [note, setNote] = useState("");
  const navigate = useNavigate();
  const qc = useQueryClient();

  const submit = useMutation({
    mutationFn: submitCheckIn,
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["runs"] }),
        qc.invalidateQueries({ queryKey: ["supportPlan"] }),
        qc.invalidateQueries({ queryKey: ["signals"] }),
      ]);
      navigate("/dashboard");
    },
  });

  const moodLabels = ["😞", "😕", "😐", "🙂", "😊"];
  const moodLabel = moodLabels[Math.min(Math.floor(mood / 2.5), 4)];

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
          <Label className="text-sm font-semibold">Mood {moodLabel}</Label>
          <Slider value={[mood]} onValueChange={([v]) => setMood(v)} min={1} max={10} step={1} />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Very low</span><span>Great</span>
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-sm font-semibold">Sleep — {sleep}h</Label>
          <Slider value={[sleep]} onValueChange={([v]) => setSleep(v)} min={0} max={12} step={0.5} />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0h</span><span>12h</span>
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-sm font-semibold">Stress level — {stress}%</Label>
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

        <Button
          onClick={() => submit.mutate({ mood, sleep_hours: sleep, stress, note })}
          disabled={submit.isPending}
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
