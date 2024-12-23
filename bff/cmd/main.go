package main

import (
	"flag"
	"fmt"
	"local/bff/pkg/metrics"
	"local/bff/pkg/prometheus"
	"local/bff/pkg/query_storage"
	"local/bff/pkg/server"
	"os"
	"path/filepath"

	"github.com/spf13/viper"
)

func main() {
	fmt.Println("Starting metrics server")
	var webappPath string

	// TODO why is webappPath configured differently from other settings?
	flag.StringVar(&webappPath, "webappPath", "", "Webapp Path")
	flag.Parse()

	if webappPath == "" {
		fmt.Fprintf(os.Stderr, "Error: webappPath is required\n")
		os.Exit(1)
	}

	if err := run(webappPath); err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
		os.Exit(1)
	}
}

func run(webappPath string) error {
	viper.SetConfigName("config")
	viper.SetConfigType("json")

	viper.AddConfigPath(".")
	err := viper.ReadInConfig()

	if err != nil {
		// TODO why panic rather than just return error?
		panic(fmt.Errorf("fatal error config file: %s", err))
	}

	rawConfig := make(map[string]interface{})
	if err := viper.Unmarshal(&rawConfig); err != nil {
		return fmt.Errorf("error unmarshaling config file: %s", err)
	}

	var config server.Config
	config.WebappPath = webappPath

	forceBypassAccessKey := os.Getenv("CRYSTALDBA_FORCE_BYPASS_ACCESS_KEY")
	config.ForceBypassAccessKey = forceBypassAccessKey == "true"

	// Get access key from environment variable with fallback to config file
	accessKey := os.Getenv("CRYSTALDBA_ACCESS_KEY")
	if !config.ForceBypassAccessKey && accessKey == "" {
		return fmt.Errorf("access key must be set via the CRYSTALDBA_ACCESS_KEY environment variable")
	}
	config.AccessKey = accessKey

	var ok bool
	// Get port from environment variable with fallback to config file
	port := os.Getenv("CRYSTALDBA_BFF_PORT")
	if port == "" {
		port, ok = rawConfig["port"].(string)
		if !ok || port == "" {
			return fmt.Errorf("port must be set via the CRYSTALDBA_BFF_PORT environment variable or in the config file")
		}
	}
	config.Port = port

	dataPath := os.Getenv("CRYSTALDBA_DATA_PATH")
	if dataPath == "" {
		dataPath, ok = rawConfig["data_path"].(string)
		if !ok || dataPath == "" {
			return fmt.Errorf("data path must be set via the CRYSTALDBA_DATA_PATH environment variable or in the config file")
		}
	}
	config.DataPath = dataPath

	prometheusURL := os.Getenv("PROMETHEUS_URL")
	if prometheusURL == "" {
		prometheusURL, ok = rawConfig["prometheus_server"].(string)
		if !ok || prometheusURL == "" {
			prometheusURL = "http://localhost:9090"
		}
	}
	config.PrometheusServer = prometheusURL

	if routes, ok := rawConfig["routes_config"].(map[string]interface{}); ok {
		config.RoutesConfig = make(map[string]server.RouteConfig)

		for key, value := range routes {

			var routeConfig server.RouteConfig

			routeMap, _ := value.(map[string]interface{})
			params := routeMap["params"].([]interface{})

			routeConfig.Params = make([]string, len(params))
			for i, param := range params {
				routeConfig.Params[i] = param.(string)
			}

			routeConfig.Options = make(map[string]string)
			options, _ := routeMap["options"].(map[string]interface{})
			for k, v := range options {
				routeConfig.Options[k] = v.(string)
			}

			routeConfig.Metrics = make(map[string]string)
			metrics, _ := routeMap["metrics"].(map[string]interface{})
			for k, v := range metrics {
				routeConfig.Metrics[k] = v.(string)
			}
			config.RoutesConfig[key] = routeConfig
		}
	}

	var timeDimGuard int
	var nonTimeDimGuard int

	// Convert float64 to int for time dimension guards
	if timeDimGuardFloat, ok := rawConfig["time_dim_guard"].(float64); ok {
		timeDimGuard = int(timeDimGuardFloat)
	} else {
		timeDimGuard = 12 // default value
	}

	if nonTimeDimGuardFloat, ok := rawConfig["non_time_dim_guard"].(float64); ok {
		nonTimeDimGuard = int(nonTimeDimGuardFloat)
	} else {
		nonTimeDimGuard = 3 // default value
	}

	config.TimeDimGuard = timeDimGuard
	config.NonTimeDimGuard = nonTimeDimGuard

	fmt.Printf("Config:\n%+v\n", config)

	metrics_repo := prometheus.New(config.PrometheusServer)
	metrics_service := metrics.CreateService(metrics_repo)

	dbPath := filepath.Join(dataPath, "crystaldb-collector.db")
	queryRepo, err := query_storage.NewSQLiteQueryStorage(dbPath)
	if err != nil {
		return fmt.Errorf("Failed to create query storage: %s", err)
	}

	server := server.CreateServer(config.RoutesConfig, metrics_service, queryRepo, config)

	if err = server.Run(); err != nil {
		return err
	}

	return nil
}
