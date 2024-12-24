package server

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"local/bff/pkg/metrics"
	"local/bff/pkg/middleware"
	"local/bff/pkg/query_storage"
	"log"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"compress/zlib"

	"github.com/go-chi/chi/v5"
	"github.com/go-playground/validator/v10"
	_ "github.com/mattn/go-sqlite3"
	collector_proto "github.com/pganalyze/collector/output/pganalyze_collector"
	"google.golang.org/protobuf/proto"
)

type Server interface {
	Run() error
}

type Config struct {
	Port                 string                 `json:"port"`
	PrometheusServer     string                 `json:"prometheus_server"`
	TimeDimGuard         int                    `json:"time_dim_guard"`
	NonTimeDimGuard      int                    `json:"non_time_dim_guard"`
	RoutesConfig         map[string]RouteConfig `json:"routes_config"`
	WebappPath           string                 `json:"webapp_path"`
	AccessKey            string                 `json:"access_key"`
	ForceBypassAccessKey bool                   `json:"force_bypass_access_key"`
	DataPath             string                 `json:"data_path"`
}

type RouteConfig struct {
	Params  []string          `json:"params"`
	Options map[string]string `json:"options"`
	Metrics map[string]string `json:"metrics"`
}

type server_imp struct {
	metrics_service metrics.Service
	query_storage   query_storage.QueryStorage
	config          Config
	inputValidator  *validator.Validate
}

type InstanceInfo struct {
	DBIdentifier string `json:"dbIdentifier"`
	SystemID     string `json:"systemId"`
	SystemScope  string `json:"systemScope"`
	SystemType   string `json:"systemType"`
}

type ValidationErrorResponse struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

const api_prefix = "/api"
const replace_prefix = "$"
const query_fp_label = "query_fp"
const query_text_label = "query_text"

const (
	SYSTEM_ID_MAX_LENGTH      = 63
	AWS_REGION_MAX_LENGTH     = 50
	CLUSTER_PREFIX_MAX_LENGTH = 11
	AWS_ACCOUNT_ID_LENGTH     = 12
	SYSTEM_SCOPE_MIN_LENGTH   = 13
	SYSTEM_SCOPE_MAX_LENGTH   = 73
)

func CORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == http.MethodOptions {
			return
		}

		next.ServeHTTP(w, r)
	})
}

func CreateServer(r map[string]RouteConfig, m metrics.Service, q query_storage.QueryStorage, config Config) Server {

	return server_imp{m, q, config, CreateValidator()}
}

func CreateValidator() *validator.Validate {

	validate := validator.New(validator.WithRequiredStructEnabled())
	validate.RegisterValidation("duration", ValidateDuration)

	validate.RegisterValidation("dbIdentifier", ValidateDbIdentifier)

	validate.RegisterValidation("databaseList", ValidateDatabaseList)

	validate.RegisterValidation("dim", ValidateDim)

	validate.RegisterValidation("filterDimSelected", ValidateFilterDimSelected)

	validate.RegisterValidation("afterStart", ValidateAfterStart)
	return validate
}

func fileExists(filePath string) bool {
	_, err := os.Stat(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return false
		}
		return false
	}
	return true
}

func (s server_imp) Run() error {
	r := chi.NewRouter()

	authMiddleware := middleware.NewAuthMiddleware(s.config.AccessKey, s.config.ForceBypassAccessKey)
	r.Use(authMiddleware.Authenticate)
	r.Use(CORS)

	r.Get("/api/v1/activity", activity_handler(s.metrics_service, s.query_storage, s.inputValidator, s.config.TimeDimGuard, s.config.NonTimeDimGuard))
	r.Get("/api/v1/instance", info_handler(s.metrics_service, s.inputValidator))
	r.Get("/api/v1/instance/database", databases_handler(s.metrics_service, s.inputValidator))
	r.Get("/api/v1/snapshots", snapshots_handler(s.config.DataPath))

	r.Route(api_prefix, func(r chi.Router) {
		r.Mount("/", metrics_handler(s.config.RoutesConfig, s.metrics_service))
	})

	fs := http.FileServer(http.Dir(s.config.WebappPath))

	r.Handle("/*", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		filePath := filepath.Join(s.config.WebappPath, r.URL.Path[1:])
		if fileExists(filePath) {
			fs.ServeHTTP(w, r)
		} else {
			http.ServeFile(w, r, filepath.Join(s.config.WebappPath, "index.html"))
		}
	}))

	return http.ListenAndServe(":"+s.config.Port, r)
}

func convertDbIdentifiersToPromQLParam(identifiers []string) string {
	if len(identifiers) == 0 {
		return ""
	}

	quoted := make([]string, len(identifiers))
	for i, id := range identifiers {
		quoted[i] = fmt.Sprintf("%s", id)
	}

	result := strings.Join(quoted, "|")

	// Add parentheses if there are multiple identifiers
	if len(identifiers) > 1 {
		result = "(" + result + ")"
	}

	return result
}

func getActualDbIdentifier(dbIdentifier string) (string, error) {
	_, systemID, _, err := splitDbIdentifier(dbIdentifier)
	return systemID, err
}

func splitDbIdentifier(dbIdentifier string) (string, string, string, error) {
	parts := strings.SplitN(dbIdentifier, "/", 3)

	if len(parts) != 3 {
		return "", "", "", fmt.Errorf("invalid dbidentifier format: %s", dbIdentifier)
	}

	systemType := parts[0]
	systemID := parts[1]
	systemScope := parts[2]

	return systemType, systemID, systemScope, nil
}

func metrics_handler(route_configs map[string]RouteConfig, metrics_service metrics.Service) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

		route := strings.TrimPrefix(r.URL.Path, api_prefix)

		start := r.URL.Query().Get("start")
		end := r.URL.Query().Get("end")

		now := time.Now()

		startTime, err := parseTimeParameter(start, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		var endTime time.Time
		if end != "" {
			endTime, err = parseTimeParameter(end, now)
			if err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
		} else {
			endTime = now
		}

		if startTime.After(endTime) {
			http.Error(w, "Parameter 'end' must be greater than 'start'", http.StatusBadRequest)
			return
		}

		options := map[string]string{
			"start": strconv.FormatInt(startTime.UnixMilli(), 10),
			"end":   strconv.FormatInt(endTime.UnixMilli(), 10),
		}
		metrics := make(map[string]string)

		if route_config, ok := route_configs[route]; ok {
			for _, param := range route_config.Params {
				value := r.URL.Query().Get(param)
				if param == "start" || param == "end" {
					continue
				}

				if param == "dbidentifier" && value == "" {
					http.Error(w, "The 'dbidentifier' parameter is required and cannot be empty.", http.StatusBadRequest)
					return
				} else if value != "" {
					all_params := []string{param}
					all_values := []string{value}
					if param == "dbidentifier" {
						systemType, systemID, systemScope, err := splitDbIdentifier(value)
						if err != nil {
							http.Error(w, "The 'dbidentifier' is malformatted.", http.StatusBadRequest)
							return
						}
						all_params = []string{param, "sys_type", "sys_id", "sys_scope"}
						all_values = []string{value, systemType, systemID, systemScope}
					}
					for metric, query := range route_config.Metrics {
						var current_query string
						if metrics[metric] == "" {
							current_query = query
						} else {
							current_query = metrics[metric]
						}

						for i, p := range all_params {
							current_query = strings.ReplaceAll(current_query, replace_prefix+p, all_values[i])
						}

						metrics[metric] = current_query

					}

					for option, input := range route_config.Options {
						var current_input string
						if options[option] == "" {
							current_input = input
						} else {
							current_input = options[option]
						}

						options[option] = strings.ReplaceAll(current_input, replace_prefix+param, value)

					}
				}

			}
			for metric, query := range metrics {
				if strings.Contains(query, replace_prefix) {
					http.Error(w, "Query for Metric: "+metric+" still contains unresolved params: "+query, http.StatusBadRequest)
					return
				}
			}

			for option, input := range options {
				if strings.Contains(input, replace_prefix) {
					http.Error(w, "Option: "+option+" still contains unresolved params: "+input, http.StatusBadRequest)
					return
				}
			}

			results, err := metrics_service.Execute(metrics, options)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}

			var metrics []map[string]interface{}

			for time, record := range results {
				metric_record := make(map[string]interface{})
				metric_record["time_ms"] = time
				for metric, value := range record {
					// Check for NaN values
					if math.IsNaN(value) {
						// Replace NaN with 0.0 for JSON compatibility
						metric_record[metric] = 0.0
					} else {
						metric_record[metric] = value
					}
				}
				metrics = append(metrics, metric_record)
			}

			sort.Slice(metrics, func(i, j int) bool {
				return metrics[i]["time_ms"].(int64) < metrics[j]["time_ms"].(int64)
			})

			js, err := json.Marshal(metrics)
			if err != nil {
				http.Error(w, fmt.Sprintf("JSON marshaling error: %v", err), http.StatusInternalServerError)
				return
			}

			currentTime := time.Now().UnixNano() / int64(time.Millisecond)
			wrappedJSON, err := WrapJSON(js, map[string]interface{}{"server_now": currentTime})
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}

			w.WriteHeader(http.StatusOK)
			w.Write(wrappedJSON)
		} else {
			http.Error(w, "No matching route found", http.StatusNotFound)
		}
	})
}

type ActivityParams struct {
	DbIdentifier string `validate:"required,dbIdentifier"`
	DatabaseList string `validate:"required,databaseList"`

	Start string `validate:"required"`
	End   string `validate:"required,afterStart"`
	Step  string `validate:"required,duration"`

	Legend            string `validate:"required,dim"`
	Dim               string `validate:"required,dim"`
	FilterDim         string `validate:"omitempty,dim"`
	FilterDimSelected string `validate:"omitempty,filterDimSelected"`

	Limit       string `validate:"omitempty,numeric,gt=0"`
	LimitLegend string `validate:"omitempty,numeric,gt=0"`

	Offset string `validate:"omitempty,numeric,gt=0"`
}

func extractPromQLInput(params ActivityParams, now time.Time) (PromQLInput, error) {

	startTime, err := parseTimeParameter(params.Start, now)
	if err != nil {
		return PromQLInput{}, err
	}

	endTime, err := parseTimeParameter(params.End, now)
	if err != nil {
		return PromQLInput{}, err
	}

	stepDuration, err := time.ParseDuration(params.Step)
	if err != nil {
		return PromQLInput{}, err
	}

	limitValue := 0
	limitLegendValue := 0
	if params.Limit != "" {
		limitValue, err = strconv.Atoi(params.Limit)
		if err != nil {
			return PromQLInput{}, err
		}
	}

	offsetValue := 0
	if params.Offset != "" {
		offsetValue, err = strconv.Atoi(params.Offset)
		if err != nil {
			return PromQLInput{}, err
		}
	}

	if params.LimitLegend != "" {
		limitLegendValue, err = strconv.Atoi(params.LimitLegend)
		if err != nil {
			return PromQLInput{}, err
		}
	}

	dbListEscaped := ""
	if params.DatabaseList != "" {
		dbListEscaped = strconv.Quote(params.DatabaseList)
		dbListEscaped = dbListEscaped[1 : len(dbListEscaped)-1]
	}

	filterDimSelectedEscaped := ""
	if params.FilterDimSelected != "" {
		filterDimSelectedEscaped = strconv.Quote(params.FilterDimSelected)
		filterDimSelectedEscaped = filterDimSelectedEscaped[1 : len(filterDimSelectedEscaped)-1]
	}

	dbIdentifierEscaped := ""
	if params.DbIdentifier != "" {
		dbIdentifierEscaped = strconv.Quote(params.DbIdentifier)
		dbIdentifierEscaped = dbIdentifierEscaped[1 : len(dbIdentifierEscaped)-1]
	}

	return PromQLInput{
		DatabaseList:      dbListEscaped,
		Start:             startTime,
		End:               endTime,
		Step:              stepDuration,
		Limit:             limitValue,
		LimitLegend:       limitLegendValue,
		Offset:            offsetValue,
		Legend:            params.Legend,
		Dim:               params.Dim,
		FilterDim:         params.FilterDim,
		FilterDimSelected: filterDimSelectedEscaped,
		DbIdentifier:      dbIdentifierEscaped,
	}, nil
}

func activity_handler(metrics_service metrics.Service, query_storage query_storage.QueryStorage, validate *validator.Validate, timeDimGuard int, nonTimeDimGuard int) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

		params := ActivityParams{
			DbIdentifier:      r.URL.Query().Get("dbidentifier"),
			DatabaseList:      r.URL.Query().Get("database_list"),
			Start:             r.URL.Query().Get("start"),
			End:               r.URL.Query().Get("end"),
			Step:              r.URL.Query().Get("step"),
			Legend:            r.URL.Query().Get("legend"),
			Dim:               r.URL.Query().Get("dim"),
			FilterDim:         r.URL.Query().Get("filterdim"),
			FilterDimSelected: r.URL.Query().Get("filterdimselected"),
			Limit:             r.URL.Query().Get("limitdim"),
			LimitLegend:       r.URL.Query().Get("limitlegend"),
			Offset:            r.URL.Query().Get("offset"),
		}

		if err := validate.Struct(params); err != nil {
			if validationErrors, ok := err.(validator.ValidationErrors); ok {
				for _, validationError := range validationErrors {
					switch validationError.Tag() {
					case "required":
						http.Error(w, fmt.Sprintf("%s is required.", validationError.Field()), http.StatusBadRequest)
						return
					case "afterStart":
						http.Error(w, "End time must be after Start time.", http.StatusBadRequest)
						return
					}
				}
			}
			// Generic error response for other validation failures
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}

		now := time.Now()
		promQLInput, err := extractPromQLInput(params, now)

		stepDuration, err := time.ParseDuration(params.Step)
		if err != nil {
			http.Error(w, "Invalid step duration format.", http.StatusBadRequest)
			return
		}

		totalDuration := promQLInput.End.Sub(promQLInput.Start)
		totalSamples := int(totalDuration / stepDuration)
		if totalSamples > 11000 {
			http.Error(w, "Maximum time samples exceeded. 11000 samples max per query", http.StatusBadRequest)
			return
		}

		if params.Dim == "time" && totalDuration > time.Duration(int64(timeDimGuard))*time.Hour {
			http.Error(w, fmt.Sprintf("Total timeframe must be less than or equal to %d hours for time dimension.", timeDimGuard), http.StatusBadRequest)
			return
		}

		if params.Dim != "time" && totalDuration > time.Duration(int64(nonTimeDimGuard))*time.Hour {
			http.Error(w, fmt.Sprintf("Total timeframe must be less than or equal to %d hours for non-time dimensions.", nonTimeDimGuard), http.StatusBadRequest)
			return
		}

		query, err := GenerateActivityCubePromQLQuery(promQLInput)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		options := map[string]string{
			"start": strconv.FormatInt(promQLInput.Start.UnixMilli(), 10),
			"end":   strconv.FormatInt(promQLInput.End.UnixMilli(), 10),
			"step":  params.Step,
			"dim":   params.Dim,
		}

		if params.LimitLegend != "" {
			options["limitlegend"] = params.LimitLegend
			options["legend"] = params.Legend
		}

		results, err := metrics_service.ExecuteRaw(query, options)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// populate query_fp with query text
		for _, result := range results {
			switch metric := result["metric"].(type) {
			case map[string]interface{}:
				result["metric"] = handleQueryFP(metric, query_storage)
			case map[string]string:
				result["metric"] = handleQueryFP(metric, query_storage)
			default:
				log.Printf("Metric not found or unsupported type: %T", metric)
			}
		}

		js, err := json.Marshal(results)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		currentTime := now.UnixMilli()
		wrappedJSON, err := WrapJSON(js, map[string]interface{}{"server_now": currentTime})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusOK)
		w.Write(wrappedJSON)

	})
}

func handleQueryFP(metric interface{}, query_storage query_storage.QueryStorage) interface{} {
	var queryFP string
	var ok bool

	switch m := metric.(type) {
	case map[string]interface{}:
		queryFP, ok = m[query_fp_label].(string)
	case map[string]string:
		queryFP, ok = m[query_fp_label]
	default:
		return metric
	}

	if !ok {
		return metric
	}

	queryText, err := query_storage.GetQuery(queryFP)
	if err != nil {
		queryText = "<not found>"
		log.Printf("Error fetching query text: %s", err)
	}

	switch m := metric.(type) {
	case map[string]interface{}:
		m[query_text_label] = queryText
	case map[string]string:
		m[query_text_label] = queryText
	}

	return metric
}

func databases_handler(metrics_service metrics.Service, validate *validator.Validate) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		dbIdentifier := r.URL.Query().Get("dbidentifier")
		err := validate.Var(dbIdentifier, "required,dbIdentifier")
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		systemType, systemID, systemScope, err := splitDbIdentifier(dbIdentifier)
		if err != nil {
			http.Error(w, "Error in splitting dbIdentifier: "+err.Error(), http.StatusBadRequest)
			return
		}

		queries := []string{
			fmt.Sprintf(`cc_all_databases{sys_id=~"%s",sys_scope=~"%s",sys_type=~"%s"}`, systemID, systemScope, systemType),
			fmt.Sprintf(`sum(cc_pg_stat_activity{sys_id=~"%s",sys_scope=~"%s",sys_type=~"%s"}) by (datname,sys_id,sys_scope,sys_type)`, systemID, systemScope, systemType),
		}

		options := make(map[string]string)
		var dbNames []string

		for _, query := range queries {
			results, err := metrics_service.ExecuteRaw(query, options)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}

			dbNames = extractDatabaseNames(results)
			if len(dbNames) > 0 {
				break
			}
		}

		js, err := json.Marshal(dbNames)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		w.Write(js)
	})
}

func extractDatabaseNames(results []map[string]interface{}) []string {
	var dbNames []string
	for _, result := range results {
		metric, ok := result["metric"].(map[string]interface{})
		if !ok {
			continue
		}
		if datname, ok := metric["datname"].(string); ok {
			if datname != "" {
				dbNames = append(dbNames, datname)
			}
		}
	}
	return dbNames
}

func info_handler(metrics_service metrics.Service, _ *validator.Validate) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		query := `count(cc_pg_stat_activity) by (sys_id, sys_scope, sys_scope_fallback,sys_type)`
		now := time.Now().UnixMilli()
		options := map[string]string{
			"start": strconv.FormatInt(now-15*60*1000, 10), // 15 minutes ago
			"end":   strconv.FormatInt(now, 10),            // now
		}

		result, err := metrics_service.ExecuteRaw(query, options)
		if err != nil {
			http.Error(w, "Error querying list of instances.", http.StatusInternalServerError)
			return
		}

		instanceInfoMap := make(map[string]InstanceInfo)

		for _, sample := range result {
			sysID := getValue(sample, "sys_id")
			sysScope := getValue(sample, "sys_scope")
			sysType := getValue(sample, "sys_type")

			dbIdentifier := sysType + "/" + sysID + "/" + sysScope

			if _, exists := instanceInfoMap[dbIdentifier]; !exists {
				instanceInfoMap[dbIdentifier] = InstanceInfo{
					DBIdentifier: dbIdentifier,
					SystemID:     sysID,
					SystemScope:  sysScope,
					SystemType:   sysType,
				}
			}
		}

		instanceInfos := []InstanceInfo{}
		for _, info := range instanceInfoMap {
			instanceInfos = append(instanceInfos, info)
		}

		info_handler_internal(instanceInfos).ServeHTTP(w, r)
	})
}

func getValue(sample map[string]interface{}, key string) string {
	if mapValue, ok := sample["metric"].(map[string]interface{}); ok {
		if value, ok := mapValue[key].(string); ok && value != "" {
			return value
		}
	}
	return ""
}

func info_handler_internal(instances []InstanceInfo) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

		response := map[string]interface{}{
			"list": instances,
		}

		js, err := json.Marshal(response)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		w.Write(js)
	})
}

func parseAndValidateInt(param string, paramName string) (int, error) {
	if param == "" {
		return 0, fmt.Errorf("Missing param/value: %s", paramName)
	}

	value, err := strconv.Atoi(param)
	if err != nil {
		return 0, fmt.Errorf("Invalid %s: %s", paramName, err.Error())
	}

	if value <= 0 {
		return 0, fmt.Errorf("%s must be a positive integer", paramName)
	}

	return value, nil
}

func WrapJSON(data []byte, metadata map[string]interface{}) ([]byte, error) {
	container := map[string]interface{}{
		"data": json.RawMessage(data),
	}

	for key, value := range metadata {
		container[key] = value
	}

	wrappedJSON, err := json.Marshal(container)
	if err != nil {
		return nil, err
	}

	return wrappedJSON, nil
}

func ValidateAfterStart(fl validator.FieldLevel) bool {
	start := fl.Parent().FieldByName("Start").String()
	end := fl.Field().String()

	now := time.Now()

	startTime, err := parseTimeParameter(start, now)
	if err != nil {
		return false
	}

	endTime, err := parseTimeParameter(end, now)
	if err != nil {
		return false
	}

	return endTime.After(startTime) || endTime.Equal(startTime)
}

func ValidateFilterDimSelected(fl validator.FieldLevel) bool {
	filterDim := fl.Parent().FieldByName("FilterDim").String()
	filterDimSelected := fl.Field().String()

	if filterDim == "Time" {
		if _, err := strconv.ParseInt(filterDimSelected, 10, 64); err == nil {
			return true
		}
		return false
	}

	// If filterDim is not "Time", accept any arbitrary string
	return len(filterDimSelected) > 0
}

func ValidateDatabaseList(fl validator.FieldLevel) bool {
	regex := `^(?:[a-zA-Z0-9_-]+|\([a-zA-Z0-9_-]+(\|[a-zA-Z0-9_-]+)*\))$`
	matched, _ := regexp.MatchString(regex, fl.Field().String())
	return matched

}

func ValidateDuration(fl validator.FieldLevel) bool {
	_, err := time.ParseDuration(fl.Field().String())
	return err == nil // Return true if parsing was successful
}

func ValidateDim(fl validator.FieldLevel) bool {
	value := fl.Field().String()
	return isValidDimension(value)
}

var validSystemTypes = []string{
	"self_hosted",
	"amazon_rds",
	"heroku",
	"google_cloudsql",
	"azure_database",
	"crunchy_bridge",
	"aiven",
	"tembo",
}
var validClusterPrefixes = []string{
	"cluster-ro-",
	"cluster-",
	"", // Allow empty cluster prefix
}

// - A dbIdentifer is defined as <SystemType>/<SystemID>/<SystemScope>
// - SystemID: min 1 char max 63char
// - SystemScope:  <AWS_REGION>/<CLUSTER_PREFIX><AWS_ACCOUNT_ID> where AWS_REGION is between 1 and 50 characters, CLUSTER_PREFIX is between 0 and 11 characters, and AWS_ACCOUNT_ID is 12 characters. Then, the whole SystemScope is betwen 13 and 73 characters.
// - SystemType: One of the following values :
//   - amazon_rds
//   - google_cloudsql
//   - azure_database
//   - heroku
//   - crunchy_bridge
//   - aiven
//   - tembo
//   - self_hosted

func ValidateDbIdentifier(fl validator.FieldLevel) bool {
	dbIdentifier := strings.TrimSpace(fl.Field().String())

	// Remove leading and trailing parentheses if they exist
	if strings.HasPrefix(dbIdentifier, "(") && strings.HasSuffix(dbIdentifier, ")") {
		dbIdentifier = dbIdentifier[1 : len(dbIdentifier)-1]
	}

	// Split by pipe for multiple identifiers
	identifiers := strings.Split(dbIdentifier, "|")

	for _, id := range identifiers {
		id = strings.TrimSpace(id)

		parts := strings.SplitN(id, "/", 3)
		if len(parts) != 3 {
			return false
		}

		systemType := parts[0]
		systemID := parts[1]
		systemScope := parts[2]

		if !isValidSystemType(systemType) {
			return false
		}

		if len(systemID) < 1 || len(systemID) > SYSTEM_ID_MAX_LENGTH {
			return false
		}

		// Split the systemScope into region and optional clusterPrefixAccountID
		scopeParts := strings.SplitN(systemScope, "/", 2)
		systemRegion := scopeParts[0]
		clusterPrefixAccountID := ""
		if len(scopeParts) > 1 {
			clusterPrefixAccountID = scopeParts[1]
		}

		if len(systemRegion) < 1 || len(systemRegion) > AWS_REGION_MAX_LENGTH {
			return false
		}

		if clusterPrefixAccountID != "" {
			if len(clusterPrefixAccountID) < AWS_ACCOUNT_ID_LENGTH {
				return false
			}

			awsAccountID := clusterPrefixAccountID[len(clusterPrefixAccountID)-AWS_ACCOUNT_ID_LENGTH:]
			clusterPrefix := clusterPrefixAccountID[:len(clusterPrefixAccountID)-AWS_ACCOUNT_ID_LENGTH]

			if !isValidClusterPrefix(clusterPrefix) {
				return false
			}

			if len(awsAccountID) != AWS_ACCOUNT_ID_LENGTH {
				return false
			}

			if len(clusterPrefixAccountID) > (CLUSTER_PREFIX_MAX_LENGTH + AWS_ACCOUNT_ID_LENGTH) {
				return false
			}
		}
	}

	return true
}

func isValidSystemType(systemType string) bool {
	for _, validType := range validSystemTypes {
		if systemType == validType {
			return true
		}
	}
	return false
}

func isValidClusterPrefix(clusterPrefix string) bool {
	for _, validPrefix := range validClusterPrefixes {
		if clusterPrefix == validPrefix {
			return true
		}
	}
	return false
}

type Snapshot struct {
	S3Location  string    `json:"s3_location"`
	CollectedAt time.Time `json:"collected_at"`
}

func snapshots_handler(dataPath string) http.HandlerFunc {
	snapshotTableNames := map[string]string{
		"full":    "snapshots",
		"compact": "compact_snapshots",
	}

	openDatabase := func(dataPath string) (*sql.DB, error) {
		dbPath := filepath.Join(dataPath, "crystaldba-collector.db")
		db, err := sql.Open("sqlite3", dbPath+"?mode=ro")
		if err != nil {
			return nil, fmt.Errorf("failed to open database: %v", err)
		}
		return db, nil
	}

	return func(w http.ResponseWriter, r *http.Request) {
		limitStr := r.URL.Query().Get("limit")
		snapshotType := r.URL.Query().Get("type")

		limit := 1 // default to 1 if not specified
		if limitStr != "" {
			parsedLimit, err := strconv.Atoi(limitStr)
			if err != nil || parsedLimit < 1 {
				http.Error(w, "Invalid limit parameter", http.StatusBadRequest)
				return
			}
			limit = parsedLimit
		}

		// Validate snapshot type
		tableName, ok := snapshotTableNames[snapshotType]
		if !ok {
			http.Error(w, "Invalid type parameter. Must be 'compact' or 'full'", http.StatusBadRequest)
			return
		}

		// Open database connection
		db, err := openDatabase(dataPath)
		if err != nil {
			http.Error(w, "Failed to open database", http.StatusInternalServerError)
			return
		}
		defer db.Close()

		// Query the snapshots from SQLite
		query := `
			SELECT s3_location, collected_at
			FROM (
				SELECT DISTINCT s3_location, collected_at
				FROM ` + tableName + `
				ORDER BY collected_at DESC
				LIMIT ?
			)
			ORDER BY collected_at ASC`
		rows, err := db.Query(query, limit)
		if err != nil {
			http.Error(w, "Database query failed: "+err.Error(), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var snapshots []Snapshot
		for rows.Next() {
			var location string
			var unixTimestamp int64
			err := rows.Scan(&location, &unixTimestamp)
			if err != nil {
				fmt.Printf("Error scanning results: %v\n", err)
				http.Error(w, "Error scanning results", http.StatusInternalServerError)
				return
			}
			snapshots = append(snapshots, Snapshot{location, time.Unix(unixTimestamp, 0)})
		}

		// For each snapshot, read the file and add its contents to the response
		var response []interface{}
		for _, snapshot := range snapshots {
			file, err := os.Open(filepath.Join(dataPath, strings.TrimPrefix(snapshot.S3Location, "storage/")))
			if err != nil {
				fmt.Printf("Error reading snapshot file: %v\n", err)
				http.Error(w, "Error reading snapshot file", http.StatusInternalServerError)
				return
			}
			defer file.Close()

			// Create a gzip reader directly from the file
			zlibReader, err := zlib.NewReader(file)
			if err != nil {
				fmt.Printf("Error creating gzip reader: %v\n", err)
				http.Error(w, "Error decompressing snapshot data", http.StatusInternalServerError)
				return
			}
			defer zlibReader.Close()

			// Read the decompressed data
			data, err := io.ReadAll(zlibReader)
			if err != nil {
				fmt.Printf("Error reading decompressed data: %v\n", err)
				http.Error(w, "Error reading decompressed data", http.StatusInternalServerError)
				return
			}

			var snapshotData interface{}

			// Determine snapshot type and unmarshal accordingly
			if snapshotType == "full" {
				fullSnapshot := &collector_proto.FullSnapshot{}
				if err := proto.Unmarshal(data, fullSnapshot); err != nil {
					fmt.Printf("Error unmarshalling full snapshot: %v\n", err)
					http.Error(w, "Error parsing full snapshot protobuf data", http.StatusInternalServerError)
					return
				}
				snapshotData = fullSnapshot
			} else { // compact
				compactSnapshot := &collector_proto.CompactSnapshot{}
				if err := proto.Unmarshal(data, compactSnapshot); err != nil {
					fmt.Printf("Error unmarshalling compact snapshot: %v\n", err)
					http.Error(w, "Error parsing compact snapshot protobuf data", http.StatusInternalServerError)
					return
				}
				snapshotData = compactSnapshot
			}
			response = append(response, snapshotData)
		}

		// Write the response
		if err := json.NewEncoder(w).Encode(response); err != nil {
			http.Error(w, "Error encoding response", http.StatusInternalServerError)
			return
		}
	}
}
