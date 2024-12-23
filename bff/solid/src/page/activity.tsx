import { Title } from "@solidjs/meta";
import { CubeActivity } from "../view/cube_activity";

export function PageActivity(title = "Activity | Crystal DBA") {
  return (
    <>
      <Title>{title}</Title>
      <section class="flex flex-col py-4 gap-y-4">
        <Header />
        <CubeActivity />
      </section>
    </>
  );
}

function Header() {
  return (
    <section class="flex gap-x-2">
      <h2 class="text-xl font-semibold">
        Database Load by Active Session Counts
      </h2>
    </section>
  );
}
