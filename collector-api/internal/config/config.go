package config

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
)

var globalConfigPath string = "collector-api-config.json" // Default config path

type Config struct {
	ServerHost string `json:"server_host"`
	ServerPort int    `json:"server_port"`
	DBPath     string `json:"db_path"`     // Path to SQLite database file
	StorageDir string `json:"storage_dir"` // Base storage directory
	APIKey     string `json:"api_key"`
	Debug      bool   `json:"debug"` // Enable or disable debug logging
}

func LoadConfig(configPath string) (*Config, error) {
	file, err := os.Open(configPath)
	if err != nil {
		log.Fatalf("Could not open config file: %v", err)
		return nil, err
	}
	defer file.Close()

	apiKey := os.Getenv("CRYSTALDBA_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("access key must be set via the CRYSTALDBA_API_KEY environment variable")
	}

	decoder := json.NewDecoder(file)
	config := Config{}
	err = decoder.Decode(&config)
	if err != nil {
		log.Fatalf("Could not decode config JSON: %v", err)
		return nil, err
	}

	config.APIKey = apiKey
	return &config, nil
}

// LoadConfigWithDefaultPath loads the config from the globalConfigPath if no path is provided
func LoadConfigWithDefaultPath() (*Config, error) {
	return LoadConfig(globalConfigPath)
}

// SetGlobalConfigPath allows setting the global config path at application startup
func SetGlobalConfigPath(configPath string) {
	globalConfigPath = configPath
}
