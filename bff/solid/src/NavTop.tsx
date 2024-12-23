import { A } from "@solidjs/router";
import { Show } from "solid-js";
import type { Anything } from "./state";

export function NavTop(props: { class?: string; children: Anything }) {
  return (
    <>
      <nav
        class={`flex flex-col sm:flex-row items-center justify-between pe-3 border-b border-zinc-500 ${props.class}`}
      >
        <A href="/" class="flex items-center gap-2" end>
          <img src="/logo.svg" alt="logo" class="h-7" />
          <span class="text-2xl font-medium">Crystal DBA</span>
        </A>
        <section class="flex flex-wrap gap-4 items-center">
          {props.children}
        </section>
      </nav>
    </>
  );
}

const showPrometheus = import.meta.env.VITE_DEV_MODE === "true";

export function NavTopConfig1() {
  return (
    <NavTop class="mb-8">
      <A
        activeClass="activeTopNav"
        href="/activity"
        class="flex items-center justify-center h-16 px-4"
        end
      >
        Activity
      </A>
      <A
        activeClass="activeTopNav"
        href="/metrics"
        class="flex items-center justify-center h-16 px-4"
        end
      >
        Metrics
      </A>

      <Show when={showPrometheus}>
        <A
          activeClass="activeTopNav"
          href="/prometheus"
          class="flex items-center justify-center h-16 px-4"
          end
        >
          Prometheus
        </A>
      </Show>
    </NavTop>
  );
}
