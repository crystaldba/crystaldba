# Metrics BFF

Exposes an api that can be configured to expose routes for executing arbitrary prometheus queries for time series results
See the configuration examples in `config.json` and `config_all.json`
`config.json` is the actual configuration the service will consume.
`config_all.json` is an example that contains all the queries we might utilize.

NOTE: There is a limit of 11 thousand samples per query. Meaning if you want data at a 5 second sample rate, you can only request a time span of 11000*5 seconds, about 15hours, in a single query. If you want data at a 30s sample rate, you can query up a 91 hour time range in a single query

## Testing

Run unit tests with: `go test ./...`
Run formatting with: `go fmt ./...`

## Setting up for Development

During development (say to attach a debugger) you may wish to run this BFF independently of the rest of the Crystal DBA project.
The BFF requires access to a running Prometheus service, which you can create either by installing the project from a release or by using the `scripts/run.sh` script.

You must identify the port that the Prometheus service is accessible on, e.g., 9090.

- Set the `PROMETHEUS_URL` environment variable with the Prometheus URL, e.g., `export PROMETHEUS_URL="http://localhost:9090"` to point the BFF to the Prometheus service.
- You may need to change the `port` in the `config.json` file to match the port the Prometheus service is running on.
- In the `bff` folder, run `go run ./cmd/main.go -webappPath <PATH_TO_FRONTEND_BUILD>` to start up the BFF. Here `<PATH_TO_FRONTEND_BUILD>` is the path to the build directory of the frontend application, and can be `/tmp` if you do not need to run a frontend. This will start up a server at the port in the `config.json` file (default port 4000, change `config.json` to if this presents a conflict).
