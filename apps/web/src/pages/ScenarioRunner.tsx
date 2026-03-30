import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getAgentRun, getScenarios, triggerScenario } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FlaskConical, Play, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import type { AgentRun } from "@/lib/types";

export default function ScenarioRunner() {
  const [selected, setSelected] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const navigate = useNavigate();
  const { data: scenarios } = useQuery({ queryKey: ["scenarios"], queryFn: getScenarios });

  const trigger = useMutation({
    mutationFn: triggerScenario,
    onSuccess: (run) => setActiveRunId(run.id),
  });

  const liveRun = useQuery({
    queryKey: ["scenario-run", activeRunId],
    queryFn: () => getAgentRun(activeRunId!),
    enabled: !!activeRunId,
    refetchInterval: (query) => {
      const run = query.state.data as AgentRun | undefined;
      if (!activeRunId) return false;
      if (!run) return 2000;
      return run.status === "pending" || run.status === "running" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (!activeRunId || !liveRun.data) return;
    if (liveRun.data.status === "completed" || liveRun.data.status === "failed") {
      navigate(`/traces/${activeRunId}`);
    }
  }, [activeRunId, liveRun.data, navigate]);

  const awaitingCompletion =
    !!activeRunId && (!liveRun.data || liveRun.data.status === "pending" || liveRun.data.status === "running");

  return (
    <div className="p-6 lg:p-10 max-w-3xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <FlaskConical className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Scenario Runner</h1>
          <p className="text-muted-foreground">Simulate care scenarios to test the agent pipeline</p>
        </div>
      </div>

      <div className="space-y-3">
        {scenarios?.map((sc, i) => (
          <motion.button
            key={sc.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            onClick={() => setSelected(sc.id)}
            className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
              selected === sc.id ? "border-primary bg-accent shadow-glow" : "border-border bg-card hover:border-primary/40"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-sm">{sc.label}</span>
              <Badge variant="outline" className="text-xs capitalize">{sc.persona.replace("_", " ")}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">{sc.description}</p>
          </motion.button>
        ))}
      </div>

      {activeRunId ? (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">Live run status</p>
              <p className="text-xs text-muted-foreground">
                Run <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">{activeRunId}</code>
                {liveRun.data?.summary ? ` · ${liveRun.data.summary}` : ""}
              </p>
            </div>
            <Badge variant="outline" className="capitalize">
              {liveRun.data?.status || "pending"}
            </Badge>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            {awaitingCompletion
              ? "Polling every 2 seconds until the run reaches a terminal state, then opening the final trace."
              : "Terminal state reached. Opening trace…"}
          </p>
        </div>
      ) : null}

      <Button
        onClick={() => selected && trigger.mutate(selected)}
        disabled={!selected || trigger.isPending || awaitingCompletion}
        className="w-full"
        size="lg"
      >
        {trigger.isPending || awaitingCompletion ? (
          <><Loader2 className="h-4 w-4 animate-spin mr-2" />Waiting for final trace…</>
        ) : (
          <><Play className="h-4 w-4 mr-2" />Run scenario</>
        )}
      </Button>
    </div>
  );
}
