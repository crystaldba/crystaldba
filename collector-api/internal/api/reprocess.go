package api

import (
	"collector-api/internal/config"
	"collector-api/internal/db"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path"
	"sort"
	"strings"
	"time"
)

func ReprocessSnapshots(cfg *config.Config, reprocessFull, reprocessCompact bool) error {
	log.Printf("Started reprocessing snapshots")
	startTime := time.Now()

	queue := GetQueueInstance()
	defer func() {
		queue.Unlock()
		if err := queue.ProcessQueue(cfg); err != nil {
			log.Printf("Error processing queued snapshots: %v", err)
		}
	}()

	var allSnapshots []SnapshotTask

	var earliestTimestamp int64
	var latestTimestamp int64

	// Collect full snapshots if requested
	if reprocessFull {
		fullSnapshots, err := db.GetAllFullSnapshots()
		if err != nil {
			return fmt.Errorf("get full snapshots: %w", err)
		}

		for _, snapshot := range fullSnapshots {
			if earliestTimestamp == 0 || snapshot.CollectedAt < earliestTimestamp {
				earliestTimestamp = snapshot.CollectedAt
			}
			if snapshot.CollectedAt > latestTimestamp {
				latestTimestamp = snapshot.CollectedAt
			}

			systemInfo := SystemInfo{
				SystemID:    snapshot.SystemID,
				SystemScope: snapshot.SystemScope,
				SystemType:  snapshot.SystemType,
			}
			snapshotSystemInfo, err := extractSystemInfoFromFullSnapshot(snapshot.S3Location)
			if err != nil {
				log.Printf("Error extracting system info from full snapshot %s: %v", snapshot.S3Location, err)
				continue
			}

			if systemInfo != snapshotSystemInfo {
				log.Printf("Warning: System info mismatch for snapshot %s. DB: %+v, Snapshot: %+v",
					snapshot.S3Location, systemInfo, snapshotSystemInfo)
			}

			allSnapshots = append(allSnapshots, SnapshotTask{
				S3Location:  snapshot.S3Location,
				CollectedAt: snapshot.CollectedAt,
				SystemInfo:  systemInfo,
				IsCompact:   false,
			})
		}
	}

	// Collect compact snapshots if requested
	if reprocessCompact {
		compactSnapshots, err := db.GetAllCompactSnapshots()
		if err != nil {
			return fmt.Errorf("get compact snapshots: %w", err)
		}

		for _, snapshot := range compactSnapshots {
			if earliestTimestamp == 0 || snapshot.CollectedAt < earliestTimestamp {
				earliestTimestamp = snapshot.CollectedAt
			}
			if snapshot.CollectedAt > latestTimestamp {
				latestTimestamp = snapshot.CollectedAt
			}

			systemInfo := SystemInfo{
				SystemID:    snapshot.SystemID,
				SystemScope: snapshot.SystemScope,
				SystemType:  snapshot.SystemType,
			}

			allSnapshots = append(allSnapshots, SnapshotTask{
				S3Location:  snapshot.S3Location,
				CollectedAt: snapshot.CollectedAt,
				SystemInfo:  systemInfo,
				IsCompact:   true,
			})
		}
	}

	// Sort all snapshots by timestamp
	sort.Slice(allSnapshots, func(i, j int) bool {
		return allSnapshots[i].CollectedAt < allSnapshots[j].CollectedAt
	})

	var targetStart time.Time
	var targetEnd time.Time

	if earliestTimestamp > 0 && latestTimestamp > 0 {
		targetStart = time.Unix(0, earliestTimestamp*int64(time.Second))
		targetEnd = time.Unix(0, latestTimestamp*int64(time.Second))
		// Limit reprocessing to 2 weeks
		twoWeeksAgo := targetEnd.Add(-14 * 24 * time.Hour)
		if targetStart.Before(twoWeeksAgo) {
			if cfg.Debug {
				log.Printf("Limiting reprocessing start time from %v to %v", targetStart, twoWeeksAgo)
			}
			targetStart = twoWeeksAgo
		}
	}

	// Filter snapshots
	filteredSnapshots := make([]SnapshotTask, 0, len(allSnapshots))
	for _, snapshot := range allSnapshots {
		if !time.Unix(0, snapshot.CollectedAt*int64(time.Second)).Before(targetStart) {
			filteredSnapshots = append(filteredSnapshots, snapshot)
		} else if cfg.Debug {
			log.Printf("Filtering out snapshot %s (system_id: %s) before start time %v",
				snapshot.S3Location, snapshot.SystemInfo.SystemID, targetStart)
		}
	}

	if err := HandleSnapshotBatches(cfg, filteredSnapshots, DefaultSnapshotBatchSize); err != nil {
		log.Printf("Error handling snapshot batches: %v", err)
	}

	log.Printf("Successfully handled snapshot batches. Took %v", time.Since(startTime))

	// Evaluate recording rules for the entire time range
	if earliestTimestamp > 0 && latestTimestamp > 0 {

		if err := EvaluateRecordingRules(cfg, targetStart, targetEnd); err != nil {
			return fmt.Errorf("Failed to evaluate recording rules: %v", err)
		}

		log.Printf("Successfully evaluated recording rules. Now, restart the prometheus service with the right configuration to enable.")
	}

	log.Printf("Reprocessing snapshots completed. Took %v", time.Since(startTime))

	return signalPrometheusConfigChange()
}

func EvaluateRecordingRules(cfg *config.Config, start, end time.Time) error {
	// Create temporary directory for rules evaluation output
	dataDir, err := os.MkdirTemp("", "prometheus-rules-*")
	if err != nil {
		return fmt.Errorf("create temp dir: %w", err)
	}
	defer os.RemoveAll(dataDir)

	// Create blocks from rules
	cmd := exec.Command("../../prometheus/promtool",
		"tsdb", "create-blocks-from", "rules",
		"--start", fmt.Sprintf("%s", start.Format(time.RFC3339)),
		"--end", fmt.Sprintf("%s", end.Format(time.RFC3339)),
		"--url", fmt.Sprintf("http://%s", prometheusURL.Host),
		"--output-dir", dataDir,
		"../../config/prometheus/recording_rules.yml")

	log.Printf("Running promtool command: %v", cmd.Args)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("create blocks from rules: %v\nOutput: %s", err, output)
	}

	if cfg.Debug {
		log.Printf("Successfully created blocks. Output: %s", output)
	}

	// Move the generated blocks from the data subdirectory to prometheus data directory
	entries, err := os.ReadDir(dataDir)
	if err != nil {
		return fmt.Errorf("read data directory: %w", err)
	}

	// Replace the existing move block code with:
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		source := path.Join(dataDir, entry.Name())
		dest := path.Join("../../prometheus_data", entry.Name())

		if err := copyDir(source, dest); err != nil {
			return fmt.Errorf("copy block %s: %w", entry.Name(), err)
		}

		// Clean up source directory after successful copy
		if err := os.RemoveAll(source); err != nil {
			log.Printf("Warning: Failed to clean up source directory %s: %v", source, err)
		}

		if cfg.Debug {
			log.Printf("Copied block %s to Prometheus data directory", entry.Name())
		}
	}

	return nil
}

func copyDir(src, dst string) error {
	// Create the destination directory
	if err := os.MkdirAll(dst, 0755); err != nil {
		return fmt.Errorf("create destination directory: %w", err)
	}

	// Read source directory
	entries, err := os.ReadDir(src)
	if err != nil {
		return fmt.Errorf("read source directory: %w", err)
	}

	for _, entry := range entries {
		srcPath := path.Join(src, entry.Name())
		dstPath := path.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := copyDir(srcPath, dstPath); err != nil {
				return fmt.Errorf("copy directory %s: %w", entry.Name(), err)
			}
		} else {
			// Copy file
			if err := copyFile(srcPath, dstPath); err != nil {
				return fmt.Errorf("copy file %s: %w", entry.Name(), err)
			}
		}
	}

	return nil
}

func copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("open source file: %w", err)
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return fmt.Errorf("create destination file: %w", err)
	}
	defer destFile.Close()

	if _, err := io.Copy(destFile, sourceFile); err != nil {
		return fmt.Errorf("copy file contents: %w", err)
	}

	// Copy file permissions
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return fmt.Errorf("get source file info: %w", err)
	}

	return os.Chmod(dst, sourceInfo.Mode())
}

func signalPrometheusConfigChange() error {
	// Get Prometheus host from environment
	prometheusHost := os.Getenv("PROMETHEUS_HOST")
	if prometheusHost == "" {
		prometheusHost = "localhost:9090"
	}

	// Extract base host without port
	host := prometheusHost
	if idx := strings.LastIndex(host, ":"); idx != -1 {
		host = host[:idx]
	}

	// Call our custom endpoint to switch to normal mode
	url := fmt.Sprintf("http://%s:7090/switch-to-normal", host)
	req, err := http.NewRequest(http.MethodPost, url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send switch request to Prometheus: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code from Prometheus switch: %d", resp.StatusCode)
	}

	log.Printf("Successfully switched Prometheus to normal configuration")

	reprocessDoneFile := os.Getenv("CRYSTALDBA_REPROCESS_DONE_FILE")

	if reprocessDoneFile == "" {
		reprocessDoneFile = "/tmp/reprocess-done"
	}

	if err := os.WriteFile(reprocessDoneFile, []byte("reprocessing done"), 0644); err != nil {
		return fmt.Errorf("failed to write reprocess done file: %w", err)
	}

	return nil
}
