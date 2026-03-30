import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Globe2,
  Loader2,
  Network,
  RotateCcw,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getAgentRun } from "@/lib/api";
import type { AgentMessage, AgentName, AgentRun } from "@/lib/types";

const agentColors: Partial<Record<AgentName, string>> = {
  coordinator: "border-primary bg-primary/5",
  signal_interpretation: "border-info bg-info/5",
  risk_stratification: "border-warning bg-warning/5",
  intervention_planning: "border-success bg-success/5",
  empathy_checkin: "border-accent-foreground bg-accent",
  validation_loop: "border-muted-foreground bg-muted",
  student_support: "border-info bg-info/5",
  caregiver_burnout: "border-warning bg-warning/5",
};

export default function TraceView() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getAgentRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const liveRun = query.state.data as AgentRun | undefined;
      if (!liveRun) return 2000;
      return liveRun.status === "pending" || liveRun.status === "running" ? 2000 : false;
    },
  });

  if (!run) {
    return (
      <div className="p-10 animate-pulse">
        <div className="h-8 w-48 rounded bg-muted" />
      </div>
    );
  }

  const coordinator = run.messages.filter((message) => message.agent_name === "coordinator");
  const parallel = run.messages.filter((message) => message.agent_type === "parallel");
  const a2a = run.messages.filter((message) => message.agent_type === "a2a");
  const loops = run.messages.filter((message) => message.agent_type === "loop");
  const local = run.messages.filter(
    (message) => message.agent_type === "local" && message.agent_name !== "coordinator",
  );
  const isLive = run.status === "pending" || run.status === "running";

  return (
    <div className="p-6 lg:p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <Link
          to="/traces"
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to traces
        </Link>
        <div className="flex items-center gap-3">
          <Network className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Agent Trace</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>
                {run.member_label || `Member #${run.user_id}`}
                {run.persona ? ` · ${run.persona.replace("_", " ")}` : ""}
              </span>
              <Badge variant="outline" className="capitalize">
                {run.status}
              </Badge>
              {run.risk_level ? (
                <Badge variant="outline" className="capitalize">
                  {run.risk_level} risk
                </Badge>
              ) : null}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Run <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{run.id}</code>
              {run.summary ? ` · ${run.summary}` : ""}
            </p>
          </div>
        </div>
      </div>

      {isLive ? (
        <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
          <Loader2 className="mt-0.5 h-4 w-4 animate-spin text-primary" />
          <div>
            <p className="text-sm font-semibold">Run still in progress</p>
            <p className="text-sm text-muted-foreground">
              Polling every 2 seconds until the final trace data is available.
            </p>
          </div>
        </div>
      ) : null}

      {run.status === "failed" ? (
        <div className="flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-4 shadow-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 text-destructive" />
          <div>
            <p className="text-sm font-semibold">Run failed</p>
            <p className="text-sm text-muted-foreground">
              {run.messages.length > 0
                ? "The coordinator stopped before producing a final plan. Review the trace below for the last successful step."
                : "No trace messages were persisted. This usually means the coordinator failed during startup or deployment bootstrap."}
            </p>
          </div>
        </div>
      ) : null}

      <FinalActionSection run={run} />

      {coordinator.length > 0 ? (
        <TraceSection title="Coordinator">
          <div className="space-y-3">
            {coordinator.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.06 }}
              >
                <TraceCard msg={message} />
              </motion.div>
            ))}
          </div>
        </TraceSection>
      ) : null}

      {parallel.length > 0 ? (
        <TraceSection title="Parallel Execution" badge="Concurrent">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {parallel.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08 }}
              >
                <TraceCard msg={message} compact />
              </motion.div>
            ))}
          </div>
        </TraceSection>
      ) : null}

      {a2a.length > 0 ? (
        <TraceSection title="Remote Specialists" badge="A2A">
          <div className="space-y-3">
            {a2a.map((message) => (
              <TraceCard key={message.id} msg={message} isA2A />
            ))}
          </div>
        </TraceSection>
      ) : null}

      {loops.length > 0 ? <LoopSection messages={loops} /> : null}

      {local.length > 0 ? (
        <TraceSection title="Local Agents">
          <div className="space-y-3">
            {local.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <TraceCard msg={message} />
              </motion.div>
            ))}
          </div>
        </TraceSection>
      ) : null}
    </div>
  );
}

function FinalActionSection({ run }: { run: AgentRun }) {
  if (!run.final_action && !run.case) return null;

  return (
    <div className="rounded-xl border border-success/20 bg-success/5 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 h-5 w-5 text-success" />
        <div className="flex-1 space-y-4">
          <div>
            <p className="text-sm font-semibold">Final action</p>
            <p className="text-sm text-muted-foreground">
              Persisted intervention and case details for this run.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {run.risk_level ? (
              <Badge variant="outline" className="capitalize">
                {run.risk_level} risk
              </Badge>
            ) : null}
            {run.case ? (
              <Badge variant="outline" className="capitalize">
                Case {run.case.status.replace("_", " ")}
              </Badge>
            ) : null}
          </div>

          {run.final_action ? (
            <>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <ActionCard title="Meal Suggestion" description={run.final_action.meal_suggestion} />
                <ActionCard title="Activity Suggestion" description={run.final_action.activity_suggestion} />
                <ActionCard title="Wellness Action" description={run.final_action.wellness_action} />
              </div>
              <div className="rounded-lg border border-success/20 bg-background/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Empathy Message</p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {run.final_action.empathy_message}
                </p>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function ActionCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-success/20 bg-background/80 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}

function TraceSection({
  title,
  badge,
  children,
}: {
  title: string;
  badge?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        {badge ? (
          <Badge variant="outline" className="text-[11px] uppercase tracking-wide">
            {badge}
          </Badge>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function TraceCard({ msg, compact, isA2A }: { msg: AgentMessage; compact?: boolean; isA2A?: boolean }) {
  const color = agentColors[msg.agent_name as AgentName] || "border-border bg-card";

  return (
    <div className={`rounded-xl border-l-4 p-4 ${color} ${compact ? "text-sm" : ""}`}>
      <div className="mb-2 flex items-center gap-2">
        {isA2A ? (
          <Globe2 className="h-3.5 w-3.5 text-info" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-muted-foreground" />
        )}
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {msg.agent_name.replace(/_/g, " ")}
        </span>
        {msg.loop_iteration ? (
          <Badge variant="outline" className="text-xs">
            Iter {msg.loop_iteration}
          </Badge>
        ) : null}
      </div>
      <p className={`leading-relaxed text-muted-foreground ${compact ? "text-xs" : "text-sm"}`}>{msg.content}</p>
    </div>
  );
}

function LoopSection({ messages }: { messages: AgentMessage[] }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <section className="space-y-3">
      <button onClick={() => setExpanded(!expanded)} className="group flex items-center gap-2">
        <RotateCcw className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Validation Loop</h2>
        <Badge variant="outline" className="text-[11px] uppercase tracking-wide">
          {messages.length} iterations
        </Badge>
        <span className="text-xs text-muted-foreground group-hover:text-foreground">
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>
      {expanded ? (
        <div className="space-y-3 border-l-2 border-muted pl-4">
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.08 }}
            >
              <TraceCard msg={message} compact />
            </motion.div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
