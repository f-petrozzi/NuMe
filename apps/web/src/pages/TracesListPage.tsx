import { useQuery } from "@tanstack/react-query";
import { getRuns } from "@/lib/api";
import { Link } from "react-router-dom";
import { Network } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function TracesListPage() {
  const { data: runs } = useQuery({
    queryKey: ["runs"],
    queryFn: getRuns,
    refetchInterval: (query) =>
      (query.state.data ?? []).some((run) => run.status === "pending" || run.status === "running")
        ? 2000
        : false,
  });

  return (
    <div className="p-6 lg:p-10 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <Network className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Agent Traces</h1>
          <p className="text-muted-foreground">Inspect agent run details and message trees</p>
        </div>
      </div>

      <div className="space-y-3">
        {!runs?.length ? (
          <div className="rounded-xl border border-dashed border-border bg-card p-6 text-sm text-muted-foreground">
            No runs yet. Submit a check-in or run a scenario to populate the trace dashboard.
          </div>
        ) : null}
        {runs?.map((run) => (
          <Link
            key={run.id}
            to={`/traces/${run.id}`}
            className="block p-4 rounded-xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-semibold text-sm">
                  {run.member_label || `Member #${run.user_id}`}
                  {run.persona ? ` · ${run.persona.replace("_", " ")}` : ""}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Run {run.id}
                  {run.risk_level ? ` · ${run.risk_level} risk` : " · Awaiting analysis"}
                  {run.scenario ? ` · ${run.scenario}` : ""}
                </p>
                {run.summary ? (
                  <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{run.summary}</p>
                ) : null}
              </div>
              <Badge variant="outline" className="capitalize">{run.status}</Badge>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
