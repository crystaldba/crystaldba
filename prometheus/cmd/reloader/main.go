package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
)

func main() {
	http.HandleFunc("/switch-to-normal", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Received request to switch to normal configuration")

		if r.Method != http.MethodPost {
			log.Printf("Invalid method: %s, expected POST", r.Method)
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Get the base directory
		parentDir := os.Getenv("PARENT_DIR")
		if parentDir == "" {
			parentDir = "/usr/local/crystaldba"
		}
		log.Printf("Using parent directory: %s", parentDir)

		// Update environment variables
		os.Setenv("CRYSTALDBA_REPROCESS_FULL_SNAPSHOTS", "false")
		os.Setenv("CRYSTALDBA_REPROCESS_COMPACT_SNAPSHOTS", "false")
		log.Printf("Updated environment variables to disable reprocessing")

		// Copy normal config to active config
		configDir := filepath.Join(parentDir, "config", "prometheus")
		normalConfig := filepath.Join(configDir, "prometheus.normal.yml")
		activeConfig := filepath.Join(configDir, "prometheus.yml")

		log.Printf("Copying config from %s to %s", normalConfig, activeConfig)

		if err := copyFile(normalConfig, activeConfig); err != nil {
			log.Printf("Failed to copy config file: %v", err)
			// Check if files exist
			if _, err := os.Stat(normalConfig); os.IsNotExist(err) {
				log.Printf("Source config file does not exist: %s", normalConfig)
			}
			if _, err := os.Stat(configDir); os.IsNotExist(err) {
				log.Printf("Config directory does not exist: %s", configDir)
			}
			http.Error(w, "Failed to update config", http.StatusInternalServerError)
			return
		}
		log.Printf("Successfully copied config file")

		// Call Prometheus reload endpoint
		log.Printf("Calling Prometheus reload endpoint")
		resp, err := http.Post("http://localhost:9090/-/reload", "application/json", nil)
		if err != nil {
			log.Printf("Failed to trigger Prometheus reload: %v", err)
			http.Error(w, "Failed to reload Prometheus", http.StatusInternalServerError)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			log.Printf("Prometheus reload returned status %d with body: %s", resp.StatusCode, string(body))
			http.Error(w, "Failed to reload Prometheus", http.StatusInternalServerError)
			return
		}

		log.Printf("Successfully switched to normal configuration and reloaded Prometheus")
		w.WriteHeader(http.StatusOK)
	})

	log.Fatal(http.ListenAndServe(":7090", nil))
}

func copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("failed to open source config: %w", err)
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return fmt.Errorf("failed to create destination config: %w", err)
	}
	defer destFile.Close()

	if _, err := io.Copy(destFile, sourceFile); err != nil {
		return fmt.Errorf("failed to copy config: %w", err)
	}

	return nil
}
