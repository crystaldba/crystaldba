import { Title } from "@solidjs/meta";
import { For } from "solid-js";
import { contextState } from "../context_state";
import { ApiEndpoint } from "../state";
import { EchartsLinechart } from "../view/echarts_linechart";

export function PagePrometheus(title = "Prometheus Metrics | Crystal DBA") {
  const { state, setState } = contextState();
  setState("apiThrottle", "needDataFor", ApiEndpoint.prometheus_metrics);

  return (
    <>
      <Title>{title}</Title>
      <section class="flex flex-col gap-y-12">
        <div class="flex flex-col p-4 gap-y-4 rounded-xl bg-neutral-100 dark:bg-neutral-800">
          <h2 class="font-medium">Prometheus Health</h2>
          <section class="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-3 gap-4">
            <For
              each={
                [
                  ["Memory", "", ["memory_usage", "memory_alloc"]],
                  ["CPU Usage", "%", ["cpu_usage"]],
                  ["Goroutines", "", ["goroutines"]],
                  ["HTTP Requests", "req/s", ["http_requests"]],
                  ["Query Performance", "s", ["query_duration_avg"]],
                  ["Time Series", "", ["active_time_series"]],
                  ["Sample Rate", "samples/s", ["samples_appended"]],
                  ["Storage", "bytes", ["storage_size", "wal_size"]],
                  ["Remote Write", "", ["remote_write_timestamp"]],
                ] as [string, string, string[]][]
              }
            >
              {([title, unit, metricList]: [string, string, string[]]) => (
                <section class="p-4 rounded-lg bg-neutral-100 dark:bg-neutral-950">
                  <h2 class="break-words">
                    {title} {unit ? `(${unit})` : ""}
                  </h2>
                  <EchartsLinechart
                    title={title}
                    metricList={metricList}
                    data={state.prometheusMetricsData}
                    class="h-80"
                  />
                </section>
              )}
            </For>
          </section>
        </div>
      </section>
    </>
  );
}
