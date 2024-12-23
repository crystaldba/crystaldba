import { Title } from "@solidjs/meta";
import { For } from "solid-js";
import { contextState } from "../context_state";
import { ApiEndpoint } from "../state";
import { EchartsLinechart } from "../view/echarts_linechart";

export function PageMetric(title = "Metrics | Crystal DBA") {
  const { state, setState } = contextState();
  setState("apiThrottle", "needDataFor", ApiEndpoint.metric);

  return (
    <>
      <Title>{title}</Title>
      <section class="flex flex-col gap-y-12">
        <div class="flex flex-col p-4 gap-y-4 rounded-xl bg-neutral-100 dark:bg-neutral-800">
          <h2 class="font-medium">Database metrics</h2>
          <section class="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-3 gap-4">
            <For
              each={
                [
                  ["Sessions", "", ["sessions"]],
                  [
                    "Tuples",
                    "",
                    [
                      "tuples_dml_deleted",
                      "tuples_dml_inserted",
                      "tuples_dml_updated",
                      "tuples_reads_returned",
                      "tuples_reads_returned_fetched",
                    ],
                  ],
                  ["Connection utilization", "", ["connection_utilization"]],
                  [
                    "Transactions",
                    "",
                    [
                      "transactions_in_progress_active_transactions",
                      "transactions_in_progress_blocked_transactions",
                      "transactions_rollback",
                    ],
                  ],
                  ["Transaction commits", "", ["transactions_commit"]],
                  ["Vacuum", "", ["vacuum_max_used_transaction_ids"]],
                  ["CPU utilization", "", ["cpu_utilization"]],
                  [
                    "IO read throughput",
                    "",
                    [
                      "io_read_throughput",
                      "io_vs_disk_blocks_hit",
                      "io_vs_disk_blocks_read",
                      "io_write_throughput",
                    ],
                  ],
                  [
                    "IOPS",
                    "",
                    [
                      "disk_current_provisioned_iops",
                      "disk_read_iops",
                      "disk_write_iops",
                    ],
                  ],
                  [
                    "Memory",
                    "",
                    [
                      "free_memory",
                      "memory_usage_other_freeable_memory",
                      "memory_usage_shared_memory",
                      "memory_usage_unused_instance_memory",
                    ],
                  ],
                  ["Free storage space", "", ["free_storage_space"]],
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
                    data={state.metricData}
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
