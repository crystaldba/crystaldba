import {
  arrange,
  distinct,
  fixedOrder,
  map,
  pivotWider,
  tidy,
} from "@tidyjs/tidy";
import { EChartsAutoSize } from "echarts-solid";
import moment from "moment-timezone";
import { Show, createMemo, mergeProps } from "solid-js";
import { contextState } from "../context_state";
import { ApiEndpoint, datazoomEventHandler, listColors } from "../state";
import { truncateString } from "../util";

export function CubeDimensionTime() {
  const { state, setState } = contextState();
  setState("apiThrottle", "needDataFor", ApiEndpoint.activity);

  const timezone = moment.tz.guess();
  const timezoneAbbreviation = moment.tz(moment(), timezone).format("z");
  const timeFormat = "HH:mm:ss [GMT]Z ";

  const eventHandlers = {
    click: (event: Event) => {
      console.log("Chart is clicked!", event);
    },
    // highlight: (event: any) => { console.log("Chart Highlight", event); },
    datazoom: datazoomEventHandler,
  };

  const base = {
    color: listColors.map((item) => item.hex),
    animation: false,
    grid: {
      left: 0,
      right: 0,
      top: 10,
      bottom: 0,
      containLabel: true,
    },
    tooltip: {
      trigger: "axis",
      formatter: (
        params: {
          color: string;
          seriesName: string | number;
          value: { [x: string]: number | string | null };
        }[],
      ) => {
        const createTooltipRow = (item: {
          color: string;
          seriesName: string | number;
          value: { [x: string]: number | string | null };
        }) => {
          const colorDot = `<span style="background-color: ${item.color};" class="inline-block w-3 h-3 rounded-full mr-2"></span>`;

          const truncatedSeriesName = truncateString(
            item.seriesName.toString(),
            80,
          );
          return `
                    <div class="flex items-center mb-1 text-gray-800">
                        ${colorDot}
                        <div class="flex-1 text-left font-medium">${truncatedSeriesName}</div>
                        <div class="ml-auto text-right font-semibold">
                            ${item.value[item.seriesName] || "-"}
                        </div>
                    </div>`;
        };

        return params.map(createTooltipRow).join("");
      },
      axisPointer: {
        type: "cross",
        animation: false,
        label: {
          backgroundColor: "#505765",
        },
      },
    },
    xAxis: {
      type: "category", // NOTE: this isn't "time" because we need to stack the bar chats below.
      axisPointer: {
        label: {
          formatter: (pointer: { value: string }) => {
            const timestamp = Number.parseInt(pointer.value, 10);
            const date = moment(timestamp);
            return `${date.format(timeFormat)}(${timezoneAbbreviation})`;
          },
        },
      },
      // axisLabel: {
      //   formatter: (value: string) => {
      //     const timestamp = Number.parseInt(value, 10);
      //     const date = moment(timestamp);
      //     return `${date.format(timeFormat).replace(/ /, "\n")}(${timezoneAbbreviation})`;
      //   },
      // },
      axisLabel: {
        rotate: 65,
        formatter: (() => {
          let lastShownDate: string | null = null;

          return (value: string) => {
            const timestamp = Number.parseInt(value, 10);
            // const date = moment(timestamp);
            const date = new Date(timestamp);
            const currentDate = `${(date.getMonth() + 1)
              .toString()
              .padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}`;
            const time = `${date.getHours().toString().padStart(2, "0")}:${date
              .getMinutes()
              .toString()
              .padStart(2, "0")}:${date
              .getSeconds()
              .toString()
              .padStart(2, "0")}`;

            if (currentDate !== lastShownDate) {
              lastShownDate = currentDate;
              return `${currentDate} ${time}`;
            }

            return time;
          };
        })(),
      },
    },
    yAxis: {
      type: "value",
    },
    // legend: {
    //   // selectedMode: true,
    //   orient: "vertical",
    //   left: 0,
    //   // top: 70,
    //   // bottom: 20,
    //   textStyle: { color: true },
    // },
  };

  const dataset = createMemo(() => {
    return tidy(
      state.activityCube.cubeData,
      (rows) =>
        Array.prototype.concat(
          ...rows.map((row) =>
            row.values.map((val) => ({
              ...row.metric,
              ...val,
            })),
          ),
        ),
      pivotWider({
        namesFrom: state.activityCube.uiLegend,
        valuesFrom: "value",
      }),
      arrange(["timestamp"]),
    );
  });

  const legendDistinct = createMemo<string[]>(() => {
    return tidy(
      state.activityCube.cubeData,
      map((row) => ({
        out: row.metric[state.activityCube.uiLegend],
      })),
      distinct(({ out }) => out),
      arrange(["out"]),
      arrange([
        // move CPU to the end of the list iff it exists
        fixedOrder((row) => row.out, ["CPU", "other"], { position: "end" }),
      ]),
      map((val) => val.out),
    ) as string[];
  });

  return (
    <section class="flex flex-col">
      <section class="h-[28rem]">
        <Show when={state.activityCube.cubeData} keyed>
          <EChartsAutoSize
            // @ts-expect-error echart's typescript support seems to throw invalid errors
            option={mergeProps(base, {
              dataset: {
                dimensions: ["timestamp", ...legendDistinct()],
                source: dataset(),
              },
              series: legendDistinct().map(() => ({
                type: "bar",
                barWidth: "50%",
                stack: "time",
              })),
              dataZoom: [
                {
                  show: false,
                  realtime: false,
                  start: state.range_begin,
                  end: state.range_end,
                },
                //
                // {
                //   type: "inside",
                //   realtime: true,
                //   start: state.range_begin,
                //   end: state.range_end,
                // },
              ],
            })}
            eventHandlers={eventHandlers}
          />
        </Show>
      </section>
      <div class="self-end mt-3 text-xs text-neutral-500">
        Number of samples: {dataset().length}
      </div>
    </section>
  );
}
