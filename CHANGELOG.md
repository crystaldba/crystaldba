# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.7.0] - 2024-12-23

### Added
- **Backfill support** to rapidly populate a Prometheus database with historical snapshots.

### Changed
- **Renamed to Crystal DBA** to reflect the current product positioning.
- **Prometheus default configuration** to limit resource usage.

### Fixed
- **Filter by query** previous release introduced a regression in filtering by query.
- **Timeseries data returned out of order** when data spans more than one day.

## [0.6.0] - 2024-12-06

### Added
- **Prometheus recording rules** to improve query performance and reduce server load.
- **Prometheus self-monitoring** for better observability of the monitoring system.
- **Support for podman-compose** as a fallback when Docker Compose is not available.
- **PostgreSQL log collection from the collector** for improved debugging capabilities.
- **2-day time range option** in the time selector for extended analysis periods.
- **Export snapshots via API** enabling external data access and integration.
- **`--no-collector` mode** in run.sh for flexible deployment options.
- **`--reprocess-full-snapshots` and `--reprocess-compact-snapshots` flags** for data reprocessing.

### Changed
- **Enhanced time selector UI** with improved usability and support for arbitrary start and end times.
- **Optimized input data collection** and PromQL queries for better performance.
- **Upgraded Prometheus** with improved query capabilities.
- **Renamed time-series labels** for better consistency.
- **Code quality improvements** with Biome linting and formatting.
- **Improved query storage architecture** by moving query text to SQLite and storing only fingerprints in Prometheus for better performance.

### Fixed
- **Stale-marker cache initialization** from Prometheus.
- **Installation script** to run from any directory.
- **Query filter options** to properly include database identifier.
- **Installation issues** affecting new deployments.

### Security
- **Added CRYSTALDBA_FORCE_BYPASS_ACCESS_KEY environment variable** for flexible authentication control during development and testing.

## [0.5.0] - 2024-11-04

### Added
- **Docker Compose support** with multiple `Dockerfile`s. This improves the architecture by running each service in a separate container.
- **Shared secret authentication between Browser and Agent**, enhancing security in communications.
- **API key support as an environment variable** for `collector-api`, providing flexible configuration options.
- **New Collector build artifact**, allowing separation of metrics collection from processing at the AutoDBA agent.

### Changed
- **Incremental Docker build improvements**, reducing build time and enhancing efficiency.
- **Service deployment changes** to improve deployment reliability.

### Fixed
- **Documentation updates**: added Google Cloud Platform usage details and missing prerequisites for improved setup guidance.

## [0.4.0] - 2024-10-15

### Added
- **PostgreSQL 12, 13, 14, 15, and 16 support**, extending compatibility to all these PostgreSQL versions.
- **Google Cloud SQL support**, enabling monitoring of databases hosted on Google Cloud SQL.

### Changed
- **README automatically updated on release**, streamlining the release process.
- **Removed AWS RDS requirement**, making AutoDBA usable without AWS credentials.
- **Removed Prometheus exporters**, now integrating fully with the Collector for time-series data handling. This is made possible after adding support for ingesting Full Snapshots from the Collector.
- **Lightweight integration tests**, ensuring basic end-to-end functionality from the database to the Collector API Server. While not comprehensive, these tests provide a foundation for validating core data flow.

## [0.3.0] - 2024-10-01

### Added
- **Support for multiple databases** allowing better management of database fleets, and also improving scalability and flexibility.
- **PII filtering** to prevent sensitive information from being collected from the query arguments.
- **SQL normalization** to ensure that similar queries are grouped together for analysis and reporting.
- **Collector API Server stubs** to enable a smoother collector integration.
- **Activity cube filters** to refine data views within the Activity Cube.
- **Longer timeframes in time bar** for improved historical data analysis in the UI.
- **UI retry logic on app start**, ensuring a seamless user experience even when the backend is delayed.

### Changed
- **Prometheus query timeout increased** for more stable data retrieval during complex queries.
- **HTML meta title updated per page** to improve user navigation.

### Fixed
- **Flaky test caused by `time.now`** to ensure test stability.
- **Handling of `dbidentifier`** between the front-end, backend, and Prometheus for consistent identification.
- **Stale-marker handling** for multi-database settings, preventing erroneous data from being displayed.
- **UI eslint errors** cleaned up for better code quality.
- **Collector populating `cc_pg_stat_activity` time-series** in Prometheus for accurate activity tracking.

### Security
- **PromQL input validation** added to improve backend security for query handling.

## [0.2.0] - 2024-09-19

### Added
- Time bar for access to historical data
- Allow operation without AWS credentials

### Changed
- Simplified packaging and installation

### Fixed
- Ensure consistent UI performance with limits and throttling

## [0.1.0] - 2024-09-06

### Added
- **Initial release** of AutoDBA for PostgreSQL.
- **Prometheus database** integration for capturing time-series metrics.
- **BFF API** for backend-for-frontend architecture.
- **RDS exporter** to gather AWS RDS-specific metrics.
- **Activity Cube UI** providing a multi-dimensional visualization of database activity.
- **Database metrics UI** to display detailed PostgreSQL database statistics.
- **System metrics UI** for tracking hardware and OS performance.
- **Basic installation scripts** for `.tar.gz`, `.deb`, and `.rpm` formats.
- **Dockerized installation** for easier deployment and testing.
