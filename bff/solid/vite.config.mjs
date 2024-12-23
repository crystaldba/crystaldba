import { defineConfig } from "vite";
import solidPlugin from "vite-plugin-solid";
// import devtools from "solid-devtools/vite";

export default defineConfig({
  plugins: [
    /*
    Uncomment the following line to enable solid-devtools.
    For more info see https://github.com/thetarnav/solid-devtools/tree/main/packages/extension#readme
    */
    // devtools(),
    solidPlugin(),
  ],
  resolve: {
    alias: {
      "~": "/src",
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:5000/",
        secure: false,
        headers: {
          "Crystaldba-Access-Key":
            process.env.VITE_ACCESS_KEY || "DEFAULT-ACCESS-KEY",
        },
        //"pathRewrite": { "^/api": "" }
      },
    },
  },
  build: {
    target: "esnext",
  },
});
