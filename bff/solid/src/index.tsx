/* @refresh reload */
import { render } from "solid-js/web";

// import { attachDevtoolsOverlay } from "@solid-devtools/overlay";
// attachDevtoolsOverlay({
//   defaultOpen: false, // or alwaysOpen
//   noPadding: true,
// });

import "./index.css";
import { MetaProvider, Title } from "@solidjs/meta";
import App from "./App";

const root = document.getElementById("root");

if (import.meta.env.DEV && !(root instanceof HTMLElement)) {
  throw new Error(
    "Root element not found. Did you forget to add it to your index.html? Or maybe the id attribute got misspelled?",
  );
}

if (root)
  render(
    () => (
      <MetaProvider>
        <Title>Crystal DBA</Title>
        <App />
      </MetaProvider>
    ),
    root,
  );
