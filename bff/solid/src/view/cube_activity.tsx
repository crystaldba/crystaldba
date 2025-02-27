import { arrange, distinct, fixedOrder, map, tidy } from "@tidyjs/tidy";
import {
  For,
  type JSX,
  Match,
  Show,
  Switch,
  createEffect,
  createMemo,
  createSignal,
  on,
  onCleanup,
  onMount,
  untrack,
} from "solid-js";
import { produce } from "solid-js/store";
import { contextState } from "../context_state";
import { queryFilterOptionsOldRelativeToNow } from "../http";
import { queryFilterOptions } from "../http_simple";
import {
  type ActivityCube,
  type CubeData,
  DimensionField,
  DimensionName,
  DimensionRef,
  listColors,
  listDimensionTabNames,
} from "../state";
import { DimensionBars } from "./cube_activity_bars";
import { CubeDimensionTime } from "./cube_activity_time";

const MAX_WIDTH = 500;

export const cssSelectorGeneralBase =
  "border border-zinc-200 bg-backgroundlite dark:border-zinc-600 dark:bg-zinc-800";

export const cssSelectorGeneralHover =
  "dark:hover:bg-zinc-700 hover:bg-zinc-300";

export const cssSelectorGeneral = `${cssSelectorGeneralBase} ${cssSelectorGeneralHover} first:rounded-s-lg last:rounded-e-lg`;

export type ILegend = {
  item: string;
  colorText: string;
  colorBg: string;
}[];

type DropdownOptionData = [string, string, string, string];
const noValue = "";

export function CubeActivity() {
  const { state } = contextState();

  const legendDistinct = createMemo((): ILegend => {
    return tidy(
      state.activityCube.cubeData,
      distinct((row) => row.metric[state.activityCube.uiLegend]),
      map((row) => ({
        item: row.metric[state.activityCube.uiLegend],
      })),
      // filter(({ item }) => !!item),
      arrange(["item"]),
      arrange([
        // move CPU to the end of the list iff it exists
        fixedOrder((row) => row.item, ["CPU", "other"], { position: "end" }),
      ]),
      map((item, index) => ({
        item: item.item || "Unknown Item",
        colorText: listColors[index]?.text || "",
        colorBg: listColors[index]?.bg || "",
      })),
    );
  });

  createEffect(
    on(
      () => state.activityCube.uiFilter1,
      () => {
        untrack(() =>
          import.meta.env.VITE_DEV_MODE === "true"
            ? queryFilterOptions()
            : queryFilterOptionsOldRelativeToNow(),
        );
      },
      { defer: true },
    ),
  );

  const cssSectionHeading = "flex flex-col gap-y-3.5";

  return (
    <section class="flex flex-col-reverse md:flex-row items-start gap-8">
      <section class={`max-w-[24rem] ${cssSectionHeading}`}>
        <h2 class="font-medium text-lg">Legend</h2>
        <SelectButton label="Slice By:" dimension={DimensionField.uiLegend} />
        <Legend legend={legendDistinct()} />
      </section>
      <section class="flex flex-col gap-5 w-full">
        <section class={cssSectionHeading}>
          <h2 class="font-medium text-lg">Dimensions</h2>
          <DimensionTabs
            dimension="uiDimension1"
            cubeData={state.activityCube.cubeData}
          />

          <aside
            class={`text-2xs text-neutral-700 dark:text-neutral-300 ${
              Object.getOwnPropertyNames(state.apiThrottle.requestInFlight)
                .length
                ? "visible"
                : "invisible"
            }`}
          >
            Updating
          </aside>
        </section>
        <Dimension1
          cubeData={state.activityCube.cubeData}
          legend={legendDistinct()}
        />
      </section>
    </section>
  );
}

interface PropsLegend {
  legend: ILegend;
}

function Legend(props: PropsLegend) {
  return (
    <section class="flex flex-col gap-4">
      <For each={props.legend}>
        {(item) => (
          <div class="flex items-center gap-x-3 max-w-48">
            <div class={`rounded-md size-4 shrink-0 ${item.colorBg}`} />
            <p
              class={item.colorText}
              classList={{
                "line-clamp-4 hover:line-clamp-none hover:dark:bg-backgrounddark hover:bg-backgroundlite hover:z-10 hover:rounded-md hover:p-2 hover:ps-0":
                  (item.item || "").length > 50,
              }}
            >
              {item.item}
            </p>
          </div>
        )}
      </For>
    </section>
  );
}

interface IDimension1 {
  cubeData: CubeData;
  class?: string;
  legend: ILegend;
}

function Dimension1(props: IDimension1) {
  const { state } = contextState();
  return (
    <>
      <Switch>
        <Match when={state.activityCube.uiDimension1 === DimensionName.time}>
          <div class={props.class}>
            <CubeDimensionTime />
          </div>
        </Match>
        <Match when={true}>
          <DimensionBars cubeData={props.cubeData} legend={props.legend} />
        </Match>
      </Switch>
    </>
  );
}

interface PropsDimensionTabs {
  dimension: "uiDimension1";
  cubeData: CubeData;
}

function DimensionTabs(props: PropsDimensionTabs) {
  const [rect, setRect] = createSignal({
    height: window.innerHeight,
    width: window.innerWidth,
  });

  const handlerResize = () => {
    setRect({ height: window.innerHeight, width: window.innerWidth });
  };

  onMount(() => {
    window.addEventListener("resize", handlerResize);
  });

  onCleanup(() => {
    window.removeEventListener("resize", handlerResize);
  });

  return (
    <>
      <Show
        when={rect().width < MAX_WIDTH}
        fallback={DimensionTabsHorizontal(props)}
      >
        {DimensionTabsVertical(props)}
      </Show>
    </>
  );
}

function DimensionTabsHorizontal(props: PropsDimensionTabs) {
  const { state } = contextState();

  return (
    <section class="flex flex-col gap-y-2">
      <section data-name="dimensionTabsHoriz" class="flex">
        <Tab
          value={DimensionName.time}
          txt="Time"
          selected={state.activityCube[props.dimension] === DimensionName.time}
        />
        <For each={listDimensionTabNamesWithExtra()}>
          {(value) => (
            <Tab
              value={value[0] as DimensionName}
              txt={`${value[1]}`}
              selected={state.activityCube[props.dimension] === value[0]}
            />
          )}
        </For>
      </section>

      <section
        data-name="filterSection"
        class="flex items-center gap-x-3 text-sm"
      >
        <SelectButtonFilterBy class="self-start" />
        <ViewFilterOptions cubeData={props.cubeData} class="" />
      </section>
    </section>
  );
}

function SelectButtonFilterBy(props: { class?: string }) {
  const { setState } = contextState();
  return (
    <SelectButton
      label="Filter By:"
      class={props.class}
      dimension={DimensionField.uiFilter1}
      list={[
        [DimensionName.none, "No filter", DimensionRef.none, noValue],
        ...listDimensionTabNamesWithExtra(),
      ]}
      fnOnChange={(value) => {
        setState(
          "activityCube",
          produce((dat: ActivityCube) => {
            dat[DimensionField.uiFilter1] = value;
            // biome-ignore lint/style/noNonNullAssertion: required by SolidJS
            dat.uiFilter1Value = undefined!;
          }),
        );
      }}
    />
  );
}
function DimensionTabsVertical(props: PropsDimensionTabs) {
  return (
    <div data-name="dimensionTabsVert" class="flex flex-col gap-y-4">
      <div class="flex flex-row flex-wrap gap-4">
        <SelectButton
          label=""
          dimension={DimensionField.uiDimension1}
          list={[
            [DimensionName.time, "Time", DimensionRef.none, noValue],
            ...listDimensionTabNamesWithExtra(),
          ]}
        />
        <div data-name="filterSection" class="text-sm">
          <SelectButtonFilterBy />
        </div>
      </div>
      <ViewFilterOptions cubeData={props.cubeData} class="" />
    </div>
  );
}

function Tab(props: { value: DimensionName; txt: string; selected: boolean }) {
  const { setState } = contextState();
  return (
    <button
      type="button"
      value={props.value}
      class={`grow justify-center whitespace-pre tracking-wider flex text-sm px-1 py-2 font-normala ${cssSelectorGeneral}`}
      classList={{
        "font-semibold text-fuchsia-500 bg-zinc-300 dark:bg-zinc-700":
          props.selected,
      }}
      onClick={() => setState("activityCube", "uiDimension1", props.value)}
    >
      {props.txt}
    </button>
  );
}

function ViewFilterOptions(props: { cubeData: CubeData; class?: string }) {
  const { state, setState } = contextState();
  return (
    <Show when={state.activityCube.uiFilter1 !== DimensionName.none}>
      <div class={`flex items-center gap-x-3 text-sm ${props.class} grow`}>
        <div class="flex grow items-center defaultOpen max-w-screen-sm border border-zinc-200 bg-backgroundlite dark:border-zinc-600 dark:bg-zinc-800 rounded-lg py-2 pe-2">
          <SelectSliceBy
            dimension="uiFilter1Value"
            list={optionsFilterDropdown()}
            class="defaultOpen grow"
            defaultOpen={true}
          />
        </div>
        <Show when={state.activityCube.uiFilter1Value}>
          <button
            type="button"
            class="hover:underline underline-offset-4 me-4"
            classList={{ invisible: !state.activityCube.uiFilter1Value }}
            onClick={() => {
              setState("activityCube", "uiFilter1Value", "");
            }}
          >
            clear
          </button>
        </Show>
      </div>
    </Show>
  );
}

interface PropsSelectButton {
  dimension: DimensionField;
  label:
    | number
    | boolean
    | Node
    | JSX.ArrayElement
    | (string & {})
    | null
    | undefined;
  class?: string;
  fnOnChange?: (arg0: DimensionName) => void;
  list?: DropdownOptionData[];
}

function SelectButton(props: PropsSelectButton) {
  return (
    <div
      class={`flex text-sm p-2 border-s rounded-lg ${cssSelectorGeneral} ${props.class}`}
    >
      <div class="whitespace-pre">{props.label}</div>
      <SelectSliceBy
        dimension={props.dimension}
        list={props.list}
        fnOnChange={props.fnOnChange}
        class="text-fuchsia-500"
      />
    </div>
  );
}

function SelectSliceBy(props: {
  dimension: DimensionField | "uiFilter1Value";
  class?: string;
  fnOnChange?: (arg0: DimensionName) => void;
  list?: DropdownOptionData[];
  defaultOpen?: boolean;
}) {
  const { state, setState } = contextState();
  const defaultOpen = () =>
    !!props.defaultOpen && !state.activityCube.uiFilter1Value;
  const each: () => DropdownOptionData[] = () =>
    props.list || listDimensionTabNamesWithExtra();
  return (
    <>
      <select
        data-testclass="selectSliceBy"
        size={defaultOpen() ? Math.min(10, each.length) : 0}
        onChange={(event) => {
          const value = event.target.value as DimensionName;
          if (props.fnOnChange) props.fnOnChange(value);
          else setState("activityCube", props.dimension, value);
        }}
        class={`bg-transparent px-2 focus:outline-none ${props.class}`}
        // multiple={defaultOpen()}
      >
        <For each={each()}>
          {(value) => {
            return (
              <Option
                value={value[3] || value[0]}
                txt={value[1]}
                selected={
                  state.activityCube[props.dimension] === value[0] ||
                  !!(
                    value[2] &&
                    value[3] &&
                    state.activityCube[props.dimension] === value[3]
                  )
                }
              />
            );
          }}
        </For>
      </select>
    </>
  );
}

function Option(props: { value: string; txt: string; selected: boolean }) {
  return (
    <option
      value={props.value}
      selected={props.selected || undefined}
      class="appearance-none bg-neutral-100 dark:bg-neutral-800"
    >
      {props.txt}
    </option>
  );
}

function optionsFilterDropdown(): DropdownOptionData[] {
  const { state } = contextState();

  const list: DropdownOptionData[] = (state.activityCube.filter1Options || [])
    .map((rec) => {
      const valueMain = rec.metric[state.activityCube.uiFilter1];
      const valueAlternate =
        state.activityCube.uiFilter1 === DimensionName.query &&
        Object.prototype.hasOwnProperty.call(rec.metric, DimensionRef.query)
          ? // @ts-expect-error TODO fix this type
            [DimensionRef.query, rec.metric[DimensionRef.query]]
          : [DimensionRef.none, ""];
      return [
        valueMain,
        rec.values[0]?.value
          ? `${rec.values[0].value.toFixed(1)}: ${valueMain}`
          : valueMain,
        valueAlternate[0],
        valueAlternate[1],
      ] as DropdownOptionData;
    })
    .filter(([v1, v2, _]) => !!v1 && !!v2);

  list.unshift([DimensionName.none, "no filter", DimensionRef.none, noValue]);
  return list;
}

function listDimensionTabNamesWithExtra(): [string, string, string, string][] {
  return listDimensionTabNames().map(([a, b, c]) => [a, b, c, ""]);
}
