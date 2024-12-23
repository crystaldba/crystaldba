package api

import (
	"bytes"
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"math"
	"net/http"
	"net/url"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"

	gogoproto "github.com/gogo/protobuf/proto"
	"github.com/golang/snappy"
	collector_proto "github.com/pganalyze/collector/output/pganalyze_collector"
	"github.com/prometheus/client_golang/api"
	v1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
	"github.com/prometheus/prometheus/model/value"
	"github.com/prometheus/prometheus/prompb"
)

var (
	prometheusURL = url.URL{
		Scheme: "http",
		Host:   os.Getenv("PROMETHEUS_HOST"),
		Path:   "api/v1/write",
	}
)

const (
	Unknown    = "_unknown_"
	PgInternal = "/*pg internal*/"
)

type SystemInfo struct {
	SystemID            string
	SystemIDFallback    string
	SystemScope         string
	SystemScopeFallback string
	SystemType          string
	SystemTypeFallback  string
}

type prometheusClient struct {
	*http.Client
	endpoint url.URL
}

type promResult struct {
	Metric    map[string]string
	Value     float64
	Timestamp time.Time
}

func (c *prometheusClient) Do(req *http.Request) (*http.Response, error) {
	req.Header.Set("User-Agent", "crystaldba")
	return c.Client.Do(req)
}

func (c *prometheusClient) QueryWithRetry(query string, ts time.Time, maxRetries int) ([]promResult, error) {
	result, err := c.Query(query, ts)
	if err == nil {
		return result, nil
	}

	log.Printf("Initial Prometheus query (%s) failed: %v", query, err)

	if !strings.Contains(err.Error(), "503") {
		return nil, fmt.Errorf("query Prometheus failed: %w", err)
	}

	log.Printf("Received 503 error, starting retry attempts")

	for retries := 0; retries < maxRetries; retries++ {
		waitTime := time.Second * time.Duration(retries+1)
		log.Printf("Retry attempt %d after waiting %v", retries+1, waitTime)

		time.Sleep(waitTime)
		result, err = c.Query(query, ts)

		if err == nil {
			log.Printf("Retry attempt %d successful", retries+1)
			return result, nil
		}
		log.Printf("Retry attempt %d failed: %v", retries+1, err)
	}

	return nil, fmt.Errorf("query Prometheus failed after %d retries: %w", maxRetries, err)
}

func (c *prometheusClient) Query(query string, t time.Time) ([]promResult, error) {
	// Create v1 API client
	client, err := api.NewClient(api.Config{
		Address: fmt.Sprintf("%s://%s", c.endpoint.Scheme, c.endpoint.Host),
	})
	if err != nil {
		return nil, fmt.Errorf("error creating API client: %w", err)
	}
	v1api := v1.NewAPI(client)

	// Execute query using v1 API
	ctx := context.Background()
	result, warnings, err := v1api.Query(ctx, query, t)
	if err != nil {
		return nil, fmt.Errorf("execute query: %w", err)
	}

	if len(warnings) > 0 {
		log.Printf("Warnings from query (\"%s\"): %v", query, warnings)
	}

	// Convert result to promResult format
	var results []promResult
	switch v := result.(type) {
	case model.Vector:
		for _, sample := range v {
			results = append(results, promResult{
				Metric:    convertMetric(sample.Metric),
				Value:     float64(sample.Value),
				Timestamp: sample.Timestamp.Time(),
			})
		}
	case *model.Scalar:
		results = append(results, promResult{
			Metric:    make(map[string]string),
			Value:     float64(v.Value),
			Timestamp: v.Timestamp.Time(),
		})
	case model.Matrix:
		// For matrix results, we'll take the most recent value from each series
		for _, sampleStream := range v {
			if len(sampleStream.Values) > 0 {
				lastValue := sampleStream.Values[len(sampleStream.Values)-1]
				results = append(results, promResult{
					Metric:    convertMetric(sampleStream.Metric),
					Value:     float64(lastValue.Value),
					Timestamp: lastValue.Timestamp.Time(),
				})
			}
		}
	default:
		return nil, fmt.Errorf("unsupported result type: %T", result)
	}
	return results, nil
}

// Helper function to convert model.Metric to map[string]string
func convertMetric(metric model.Metric) map[string]string {
	result := make(map[string]string)
	for k, v := range metric {
		result[string(k)] = string(v)
	}
	return result
}

func (c *prometheusClient) RemoteWrite(data []prompb.TimeSeries) (*http.Response, error) {
	// Create the write request
	payload := &prompb.WriteRequest{
		Timeseries: data,
	}

	// Marshal to protobuf
	b, err := gogoproto.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal payload: %w", err)
	}

	// Compress with snappy
	compressed := snappy.Encode(nil, b)

	// Create HTTP request
	req, err := http.NewRequest(
		http.MethodPost,
		c.endpoint.String(),
		bytes.NewBuffer(compressed),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set required headers for remote write
	req.Header.Set("Content-Encoding", "snappy")
	req.Header.Set("Content-Type", "application/x-protobuf")
	req.Header.Set("X-Prometheus-Remote-Write-Version", "0.1.0")

	// Execute request
	resp, err := c.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}

	return resp, nil
}

// Helper function to generate system-level labels
func systemLabels(systemInfo SystemInfo) []prompb.Label {
	return []prompb.Label{
		{Name: "sys_id", Value: systemInfo.SystemID},
		{Name: "sys_id_fallback", Value: systemInfo.SystemIDFallback},
		{Name: "sys_scope", Value: systemInfo.SystemScope},
		{Name: "sys_scope_fallback", Value: systemInfo.SystemScopeFallback},
		{Name: "sys_type", Value: systemInfo.SystemType},
		{Name: "sys_type_fallback", Value: systemInfo.SystemTypeFallback},
	}
}

// Helper function to create a time series
func createTimeSeries(systemInfo SystemInfo, metricName string, additionalLabels []prompb.Label, value float64, timestamp int64) prompb.TimeSeries {
	labels := []prompb.Label{
		{Name: "__name__", Value: metricName},
	}

	labels = append(labels, additionalLabels...)

	// Add system info labels
	labels = append(labels, systemLabels(systemInfo)...)

	labels = filter(labels, nonEmptyValFilter)

	// Sort labels by name
	sortLabels(labels)

	return prompb.TimeSeries{
		Labels: labels,
		Samples: []prompb.Sample{
			{
				Timestamp: timestamp,
				Value:     value,
			},
		},
	}
}

// Helper function to create multiple time series for different metrics with shared labels
func createMultipleTimeSeries(systemInfo SystemInfo, metrics map[string]float64, sharedLabels []prompb.Label, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	for metricName, value := range metrics {
		ts = append(ts, createTimeSeries(systemInfo, metricName, sharedLabels, value, timestamp))
	}
	return ts
}

// fullSnapshotMetrics processes a FullSnapshot and generates Prometheus metrics, along with individual time-series tracking
func fullSnapshotMetrics(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, collectedAt int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	snapshotTimestamp := collectedAt * 1000 // in milli-seconds

	// Process system-level statistics
	ts = append(ts, processSystemStats(snapshot, systemInfo, snapshotTimestamp)...)

	// Process database references
	ts = append(ts, processDatabaseReferences(snapshot, systemInfo, snapshotTimestamp)...)

	// Process database statistics
	ts = append(ts, processDatabaseStats(snapshot, systemInfo, snapshotTimestamp)...)

	// Process query statistics
	ts = append(ts, processQueryStats(snapshot, systemInfo, snapshotTimestamp)...)

	// Process relation and index statistics
	ts = append(ts, processRelationAndIndexStats(snapshot, systemInfo, snapshotTimestamp)...)

	// Process settings statistics
	ts = append(ts, processSettingsStats(snapshot, systemInfo, snapshotTimestamp)...)

	return ts
}

// processSystemStats generates system-level metrics from the FullSnapshot and tracks seen metrics
func processSystemStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	// Check if System field is nil
	if snapshot.System == nil {
		log.Println("Warning: snapshot.System is nil")
		return ts
	}

	// Process CPU statistics
	ts = append(ts, processCPUStats(snapshot, systemInfo, timestamp)...)

	// Process Memory statistics
	ts = append(ts, processMemoryStats(snapshot, systemInfo, timestamp)...)

	// Process Backend count statistics
	ts = append(ts, processBackendStats(snapshot, systemInfo, timestamp)...)

	// Process Network statistics
	ts = append(ts, processNetworkStats(snapshot, systemInfo, timestamp)...)

	// Process Disk statistics
	ts = append(ts, processDiskStats(snapshot, systemInfo, timestamp)...)

	// Process disk information
	ts = append(ts, processDiskInformation(snapshot, systemInfo, timestamp)...)

	// Process disk partition statistics
	ts = append(ts, processDiskPartitionStats(snapshot, systemInfo, timestamp)...)

	return ts
}

// Helper function for CPU statistics
func processCPUStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	if snapshot.System.CpuStatistics != nil {
		for _, cpuStat := range snapshot.System.CpuStatistics {
			// Create multiple time-series for CPU usage (user, system, idle, etc.)
			ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
				"cc_system_cpu_user_percent":   cpuStat.UserPercent,
				"cc_system_cpu_system_percent": cpuStat.SystemPercent,
				"cc_system_cpu_idle_percent":   cpuStat.IdlePercent,
				"cc_system_cpu_nice_percent":   cpuStat.NicePercent,
				"cc_system_cpu_iowait_percent": cpuStat.IowaitPercent,
				"cc_system_cpu_irq_percent":    cpuStat.IrqPercent,
			}, []prompb.Label{
				{Name: "cpu_id", Value: strconv.Itoa(int(cpuStat.CpuIdx))},
			}, timestamp)...)
		}
	} else {
		log.Println("Warning: snapshot.System.CpuStatistics is nil")
	}
	return ts
}

// Helper function for Memory statistics
func processMemoryStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	if snapshot.System.MemoryStatistic != nil {
		// Create multiple time-series for all memory statistics
		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_system_memory_total_bytes":           float64(snapshot.System.MemoryStatistic.TotalBytes),
			"cc_system_memory_free_bytes":            float64(snapshot.System.MemoryStatistic.FreeBytes),
			"cc_system_memory_cached_bytes":          float64(snapshot.System.MemoryStatistic.CachedBytes),
			"cc_system_memory_buffers_bytes":         float64(snapshot.System.MemoryStatistic.BuffersBytes),
			"cc_system_memory_dirty_bytes":           float64(snapshot.System.MemoryStatistic.DirtyBytes),
			"cc_system_memory_writeback_bytes":       float64(snapshot.System.MemoryStatistic.WritebackBytes),
			"cc_system_memory_slab_bytes":            float64(snapshot.System.MemoryStatistic.SlabBytes),
			"cc_system_memory_mapped_bytes":          float64(snapshot.System.MemoryStatistic.MappedBytes),
			"cc_system_memory_page_tables_bytes":     float64(snapshot.System.MemoryStatistic.PageTablesBytes),
			"cc_system_memory_active_bytes":          float64(snapshot.System.MemoryStatistic.ActiveBytes),
			"cc_system_memory_inactive_bytes":        float64(snapshot.System.MemoryStatistic.InactiveBytes),
			"cc_system_memory_swap_used_bytes":       float64(snapshot.System.MemoryStatistic.SwapUsedBytes),
			"cc_system_memory_swap_total_bytes":      float64(snapshot.System.MemoryStatistic.SwapTotalBytes),
			"cc_system_memory_huge_pages_size_bytes": float64(snapshot.System.MemoryStatistic.HugePagesSizeBytes),
		}, nil, timestamp)...)
	} else {
		log.Println("Warning: snapshot.System.MemoryStatistic is nil")
	}
	return ts
}

// Helper function for Backend count statistics
func processBackendStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	if snapshot.BackendCountStatistics != nil {
		for _, backendStat := range snapshot.BackendCountStatistics {
			// Create labels for backend type and state
			labels := []prompb.Label{
				{Name: "backend_type", Value: backendTypeToString(backendStat.BackendType)},
			}

			processRoleName(snapshot, backendStat, &labels)
			processDatabaseName(snapshot, backendStat, &labels)

			labels = append(labels, prompb.Label{Name: "state", Value: backendStateToString(backendStat.State)})

			if backendStat.WaitingForLock {
				labels = append(labels, prompb.Label{Name: "waiting_for_lock", Value: "true"})
			}

			// Create a time-series for backend count
			ts = append(ts, createTimeSeries(systemInfo, "cc_backend_count", labels, float64(backendStat.Count), timestamp))
		}
	} else {
		log.Println("Warning: snapshot.BackendCountStatistics is nil")
	}
	return ts
}

// Helper function to process role name
func processRoleName(snapshot *collector_proto.FullSnapshot, backendStat *collector_proto.BackendCountStatistic, labels *[]prompb.Label) {
	roleName := Unknown
	if backendStat.HasRoleIdx {
		if snapshot.RoleReferences != nil && len(snapshot.RoleReferences) > int(backendStat.RoleIdx) {
			roleName = snapshot.RoleReferences[backendStat.RoleIdx].Name
			*labels = append(*labels, prompb.Label{Name: "role", Value: roleName})
		} else {
			log.Println("Warning: snapshot.RoleReferences is nil or index out of range")
		}
	}
}

// Helper function to process database name
func processDatabaseName(snapshot *collector_proto.FullSnapshot, backendStat *collector_proto.BackendCountStatistic, labels *[]prompb.Label) {
	databaseName := Unknown
	if backendStat.HasDatabaseIdx {
		if snapshot.DatabaseReferences != nil && len(snapshot.DatabaseReferences) > int(backendStat.DatabaseIdx) {
			databaseName = snapshot.DatabaseReferences[backendStat.DatabaseIdx].Name
			*labels = append(*labels, prompb.Label{Name: "datname", Value: databaseName})
		} else {
			log.Println("Warning: snapshot.DatabaseReferences is nil or index out of range")
		}
	}
}

// Helper function for Network statistics
func processNetworkStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	if snapshot.System.NetworkStatistics != nil {
		for _, netStat := range snapshot.System.NetworkStatistics {
			// Create multiple time-series for network I/O statistics
			ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
				"cc_system_network_receive_bytes_per_second":  float64(netStat.ReceiveThroughputBytesPerSecond),
				"cc_system_network_transmit_bytes_per_second": float64(netStat.TransmitThroughputBytesPerSecond),
			}, []prompb.Label{
				{Name: "interface_name", Value: snapshot.System.NetworkReferences[netStat.NetworkIdx].InterfaceName},
			}, timestamp)...)
		}
	}
	return ts
}

// Helper function for Disk statistics
func processDiskStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries
	if snapshot.System.DiskStatistics != nil {
		for _, diskStat := range snapshot.System.DiskStatistics {
			ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
				"cc_system_disk_read_ops_per_second":    diskStat.ReadOperationsPerSecond,
				"cc_system_disk_write_ops_per_second":   diskStat.WriteOperationsPerSecond,
				"cc_system_disk_read_bytes_per_second":  diskStat.BytesReadPerSecond,
				"cc_system_disk_write_bytes_per_second": diskStat.BytesWrittenPerSecond,
				"cc_system_disk_avg_read_latency":       diskStat.AvgReadLatency,
				"cc_system_disk_avg_write_latency":      diskStat.AvgWriteLatency,
				"cc_system_disk_utilization_percent":    diskStat.UtilizationPercent,
			}, []prompb.Label{
				{Name: "disk_idx", Value: strconv.Itoa(int(diskStat.DiskIdx))},
			}, timestamp)...)
		}
	}
	return ts
}

// Helper function for Disk Information
func processDiskInformation(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	for _, diskInfo := range snapshot.System.DiskInformations {
		labels := []prompb.Label{
			{Name: "disk_idx", Value: strconv.Itoa(int(diskInfo.DiskIdx))},
			{Name: "disk_type", Value: diskInfo.DiskType},
		}

		if diskInfo.Scheduler != "" {
			labels = append(labels, prompb.Label{Name: "scheduler", Value: diskInfo.Scheduler})
		}

		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_system_diskinfo_provisioned_iops": float64(diskInfo.ProvisionedIops),
			// "cc_system_disk_encrypted":        boolToFloat64(diskInfo.Encrypted),
		}, labels, timestamp)...)
	}

	return ts
}

// Helper function for Disk Partition statistics
func processDiskPartitionStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	// Create maps for quick lookup of partition references and information
	partitionRefs := make(map[int32]string)
	for idx, ref := range snapshot.System.DiskPartitionReferences {
		partitionRefs[int32(idx)] = ref.Mountpoint
	}

	partitionInfos := make(map[int32]*collector_proto.DiskPartitionInformation)
	for _, info := range snapshot.System.DiskPartitionInformations {
		partitionInfos[info.DiskPartitionIdx] = info
	}

	for _, partStat := range snapshot.System.DiskPartitionStatistics {
		mountpoint := partitionRefs[partStat.DiskPartitionIdx]
		info := partitionInfos[partStat.DiskPartitionIdx]

		labels := []prompb.Label{
			{Name: "disk_partition_idx", Value: strconv.Itoa(int(partStat.DiskPartitionIdx))},
			{Name: "mountpoint", Value: mountpoint},
		}

		if info != nil {
			labels = append(labels, []prompb.Label{
				{Name: "disk_idx", Value: strconv.Itoa(int(info.DiskIdx))},
				{Name: "filesystem_type", Value: info.FilesystemType},
				{Name: "filesystem_opts", Value: info.FilesystemOpts},
				{Name: "partition_name", Value: info.PartitionName},
			}...)
		}

		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_system_diskpartition_free_bytes":  float64(partStat.TotalBytes) - float64(partStat.UsedBytes),
			"cc_system_diskpartition_total_bytes": float64(partStat.TotalBytes),
		}, labels, timestamp)...)
	}

	return ts
}

// Helper function to convert BackendType enum to string
func backendTypeToString(backendType collector_proto.BackendCountStatistic_BackendType) string {
	switch backendType {
	case collector_proto.BackendCountStatistic_CLIENT_BACKEND:
		return "client_backend"
	case collector_proto.BackendCountStatistic_AUTOVACUUM_LAUNCHER:
		return "autovacuum_launcher"
	case collector_proto.BackendCountStatistic_AUTOVACUUM_WORKER:
		return "autovacuum_worker"
	case collector_proto.BackendCountStatistic_BACKGROUND_WRITER:
		return "background_writer"
	case collector_proto.BackendCountStatistic_CHECKPOINTER:
		return "checkpointer"
	case collector_proto.BackendCountStatistic_WALWRITER:
		return "walwriter"
	// Add other cases as necessary
	default:
		return Unknown
	}
}

// Helper function to convert BackendState enum to string
func backendStateToString(state collector_proto.BackendCountStatistic_BackendState) string {
	switch state {
	case collector_proto.BackendCountStatistic_ACTIVE:
		return "active"
	case collector_proto.BackendCountStatistic_IDLE:
		return "idle"
	case collector_proto.BackendCountStatistic_IDLE_IN_TRANSACTION:
		return "idle_in_transaction"
	case collector_proto.BackendCountStatistic_IDLE_IN_TRANSACTION_ABORTED:
		return "idle_in_transaction_aborted"
	case collector_proto.BackendCountStatistic_FASTPATH_FUNCTION_CALL:
		return "fastpath_function_call"
	case collector_proto.BackendCountStatistic_DISABLED:
		return "disabled"
	// Add other states as necessary
	default:
		return Unknown
	}
}

// processDatabaseStats generates metrics for each database in the FullSnapshot and tracks seen metrics
func processDatabaseStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	for _, dbStat := range snapshot.DatabaseStatictics {
		dbName := snapshot.DatabaseReferences[dbStat.DatabaseIdx].Name
		// Create multiple time-series for transaction commit, rollback, and frozen XID age
		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_db_xact_commit":    float64(dbStat.XactCommit),
			"cc_db_xact_rollback":  float64(dbStat.XactRollback),
			"cc_db_frozen_xid_age": float64(dbStat.FrozenxidAge),
		}, []prompb.Label{
			{Name: "datname", Value: dbName},
		}, timestamp)...)
	}

	return ts
}

func processDatabaseReferences(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	for _, dbRef := range snapshot.DatabaseReferences {
		labels := []prompb.Label{
			{Name: "datname", Value: dbRef.Name},
		}

		ts = append(ts, createTimeSeries(systemInfo, "cc_all_databases", labels, 1, timestamp))
	}

	return ts
}

// processQueryStats generates metrics for each query in the FullSnapshot and tracks seen metrics
func processQueryStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	for _, queryStat := range snapshot.QueryStatistics {
		query := snapshot.QueryInformations[queryStat.QueryIdx].GetNormalizedQuery()
		// Create multiple time-series for query calls and total time
		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_query_calls":              float64(queryStat.Calls),
			"cc_query_total_time_seconds": queryStat.TotalTime,
		}, []prompb.Label{
			{Name: "query", Value: query},
		}, timestamp)...)
	}

	return ts
}

func convertTimestampToMilliseconds(timestamp *collector_proto.NullTimestamp) float64 {
	if timestamp == nil {
		return 0
	}
	innerTs := timestamp.GetValue()
	if innerTs == nil {
		return 0
	}
	return float64(innerTs.Seconds*1000 + int64(innerTs.Nanos)/1000000)
}

// processRelationAndIndexStats generates relation and index statistics and tracks seen metrics
func processRelationAndIndexStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	for _, relStat := range snapshot.RelationStatistics {
		relationName := snapshot.RelationReferences[relStat.RelationIdx].RelationName
		schemaName := snapshot.RelationReferences[relStat.RelationIdx].SchemaName
		databaseName := snapshot.DatabaseReferences[snapshot.RelationReferences[relStat.RelationIdx].DatabaseIdx].GetName()
		// Create multiple time-series for relation size and sequential scan count
		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_relation_size_bytes":          float64(relStat.SizeBytes),
			"cc_relation_idx_scan":            float64(relStat.IdxScan),
			"cc_relation_seq_scan":            float64(relStat.SeqScan),
			"cc_relation_seq_tup_read":        float64(relStat.SeqTupRead),
			"cc_relation_idx_tup_fetch":       float64(relStat.IdxTupFetch),
			"cc_relation_n_tup_ins":           float64(relStat.NTupIns),
			"cc_relation_n_tup_upd":           float64(relStat.NTupUpd),
			"cc_relation_n_tup_del":           float64(relStat.NTupDel),
			"cc_relation_n_tup_hot_upd":       float64(relStat.NTupHotUpd),
			"cc_relation_n_live_tup":          float64(relStat.NLiveTup),
			"cc_relation_n_dead_tup":          float64(relStat.NDeadTup),
			"cc_relation_n_mod_since_analyze": float64(relStat.NModSinceAnalyze),
			"cc_relation_n_ins_since_vacuum":  float64(relStat.NInsSinceVacuum),
			"cc_relation_heap_blks_read":      float64(relStat.HeapBlksRead),
			"cc_relation_heap_blks_hit":       float64(relStat.HeapBlksHit),
			"cc_relation_idx_blks_read":       float64(relStat.IdxBlksRead),
			"cc_relation_idx_blks_hit":        float64(relStat.IdxBlksHit),
			"cc_relation_toast_blks_read":     float64(relStat.ToastBlksRead),
			"cc_relation_toast_blks_hit":      float64(relStat.ToastBlksHit),
			"cc_relation_tidx_blks_read":      float64(relStat.TidxBlksRead),
			"cc_relation_tidx_blks_hit":       float64(relStat.TidxBlksHit),
			"cc_relation_toast_size_bytes":    float64(relStat.ToastSizeBytes),
			"cc_relation_analyzed_at":         convertTimestampToMilliseconds(relStat.AnalyzedAt),
			"cc_relation_frozenxid_age":       float64(relStat.FrozenxidAge),
			"cc_relation_minmxid_age":         float64(relStat.MinmxidAge),

			// Statistics that are infrequently updated (e.g. by VACUUM, ANALYZE, and a few DDL commands)
			"cc_relation_relpages":         float64(relStat.Relpages),
			"cc_relation_reltuples":        float64(relStat.Reltuples),
			"cc_relation_relfrozenxid":     float64(relStat.Relfrozenxid),
			"cc_relation_relminmxid":       float64(relStat.Relminmxid),
			"cc_relation_last_vacuum":      convertTimestampToMilliseconds(relStat.LastVacuum),
			"cc_relation_last_autovacuum":  convertTimestampToMilliseconds(relStat.LastAutovacuum),
			"cc_relation_last_analyze":     convertTimestampToMilliseconds(relStat.LastAnalyze),
			"cc_relation_last_autoanalyze": convertTimestampToMilliseconds(relStat.LastAutoanalyze),
			"cc_relation_toast_reltuples":  float64(relStat.ToastReltuples),
			"cc_relation_toast_relpages":   float64(relStat.ToastRelpages),
		}, []prompb.Label{
			{Name: "datname", Value: databaseName},
			{Name: "schema", Value: schemaName},
			{Name: "relation", Value: relationName},
		}, timestamp)...)
	}

	for _, idxStat := range snapshot.IndexStatistics {
		indexName := snapshot.IndexReferences[idxStat.IndexIdx].IndexName
		// Create multiple time-series for index size and scan count
		ts = append(ts, createMultipleTimeSeries(systemInfo, map[string]float64{
			"cc_index_size_bytes": float64(idxStat.SizeBytes),
			"cc_index_scan_count": float64(idxStat.IdxScan),
		}, []prompb.Label{
			{Name: "index", Value: indexName},
		}, timestamp)...)
	}

	return ts
}

// processSettingsStats generates metrics for each setting in the FullSnapshot and tracks seen metrics
func processSettingsStats(snapshot *collector_proto.FullSnapshot, systemInfo SystemInfo, timestamp int64) []prompb.TimeSeries {
	var ts []prompb.TimeSeries

	for _, setting := range snapshot.Settings {
		labels := []prompb.Label{
			{Name: "name", Value: setting.Name},
			// {Name: "source", Value: setting.Source.GetValue()},
		}

		// if setting.SourceFile != nil && setting.SourceFile.Valid {
		// 	labels = append(labels, prompb.Label{Name: "source_file", Value: setting.SourceFile.Value})
		// }

		// if setting.SourceLine != nil && setting.SourceLine.Valid {
		// 	labels = append(labels, prompb.Label{Name: "source_line", Value: setting.SourceLine.Value})
		// }

		if setting.Unit != nil && setting.Unit.Valid {
			labels = append(labels, prompb.Label{Name: "unit", Value: setting.Unit.Value})
		}

		// Add current_value metric
		ts = append(ts, createTimeSeries(systemInfo, "cc_pgsetting_current_value", labels, parseSettingValue(setting.CurrentValue), timestamp))

		// Add boot_value metric if it exists and is different from current_value
		if setting.BootValue != nil && setting.BootValue.Valid && setting.BootValue.Value != setting.CurrentValue {
			ts = append(ts, createTimeSeries(systemInfo, "cc_pgsetting_boot_value", labels, parseSettingValue(setting.BootValue.Value), timestamp))
		}

		// Add reset_value metric if it exists and is different from current_value
		if setting.ResetValue != nil && setting.ResetValue.Valid && setting.ResetValue.Value != setting.CurrentValue {
			ts = append(ts, createTimeSeries(systemInfo, "cc_pgsetting_reset_value", labels, parseSettingValue(setting.ResetValue.Value), timestamp))
		}
	}

	return ts
}

// Helper function to parse setting value to float64
func parseSettingValue(value string) float64 {
	floatValue, err := strconv.ParseFloat(value, 64)
	if err != nil {
		// Handle non-numeric values (e.g., "on", "off") by using 1 for "on" and 0 for others
		if strings.ToLower(value) == "on" {
			return 1
		}
		return 0
	}
	return floatValue
}

// BackendKey uniquely identifies a backend session
type BackendKey struct {
	ApplicationName  string
	BackendType      string
	ClientAddr       string
	Datname          string
	QueryFingerPrint string
	Role             string
	State            string
	WaitEvent        string
	WaitEventType    string
}

// Hash generates a consistent string representation of the BackendKey
func (bk BackendKey) Hash() string {
	// Using strings.Builder for efficient string concatenation
	var b strings.Builder
	b.WriteString(bk.ApplicationName)
	b.WriteByte(0)
	b.WriteString(bk.BackendType)
	b.WriteByte(0)
	b.WriteString(bk.ClientAddr)
	b.WriteByte(0)
	b.WriteString(bk.QueryFingerPrint)
	b.WriteByte(0)
	b.WriteString(bk.Role)
	b.WriteByte(0)
	b.WriteString(bk.State)
	b.WriteByte(0)
	b.WriteString(bk.WaitEvent)
	b.WriteByte(0)
	b.WriteString(bk.WaitEventType)
	b.WriteByte(0)
	b.WriteString(bk.Datname)
	return b.String()
}

func getWaitEventName(waitEventType, waitEvent string) string {
	if waitEventType == "" && waitEvent == "" {
		return "CPU"
	}
	return waitEventType + ":" + waitEvent
}

// createLabelsForBackend generates Prometheus labels for a given BackendKey
// This function is used for both active backends and stale markers
func createLabelsForBackend(backendKey BackendKey, systemInfo SystemInfo) []prompb.Label {

	labels := append(systemLabels(systemInfo), []prompb.Label{
		{Name: "__name__", Value: "cc_pg_stat_activity"},
		{Name: "application_name", Value: defaultString(backendKey.ApplicationName, PgInternal)},
		{Name: "backend_type", Value: defaultString(backendKey.BackendType, PgInternal)},
		{Name: "client_addr", Value: defaultString(backendKey.ClientAddr, PgInternal)},
		{Name: "query_fp", Value: base64.StdEncoding.EncodeToString([]byte(backendKey.QueryFingerPrint))},
		{Name: "state", Value: backendKey.State},
		{Name: "usename", Value: defaultString(backendKey.Role, PgInternal)},
		{Name: "wait_event_name", Value: getWaitEventName(backendKey.WaitEventType, backendKey.WaitEvent)},
	}...)

	if backendKey.Datname != "" {
		labels = append(labels, prompb.Label{Name: "datname", Value: backendKey.Datname})
	}

	labels = filter(labels, nonEmptyValFilter)

	sortLabels(labels)
	return labels
}

// Helper function to return default value if string is empty
func defaultString(s, defaultVal string) string {
	if s == "" {
		return defaultVal
	}
	return s
}

// compactSnapshotMetrics processes a compact snapshot and returns time series for each backend
// It also returns a map of seen backends for stale marker generation
func compactSnapshotMetrics(snapshot *collector_proto.CompactSnapshot, systemInfo SystemInfo, collectedAt int64) []prompb.TimeSeries {
	snapshotTimestamp := collectedAt * 1000 // in milliseconds
	baseRef := snapshot.GetBaseRefs()
	backendCounts := make(map[string]float64)
	var firstBackendOfType = make(map[string]*BackendKey)

	for _, backend := range snapshot.GetActivitySnapshot().GetBackends() {
		// Create a unique BackendKey for each backend
		backendKey := BackendKey{
			ApplicationName: backend.GetApplicationName(),
			BackendType:     backend.GetBackendType(),
			ClientAddr:      backend.GetClientAddr(),
			State:           backend.GetState(),
			WaitEvent:       backend.GetWaitEvent(),
			WaitEventType:   backend.GetWaitEventType(),
		}

		if baseRef != nil {
			if backend.GetHasRoleIdx() {
				backendKey.Role = baseRef.GetRoleReferences()[backend.GetRoleIdx()].GetName()
			}
			if backend.GetHasDatabaseIdx() {
				backendKey.Datname = baseRef.GetDatabaseReferences()[backend.GetDatabaseIdx()].GetName()
			}
			if backend.GetHasQueryIdx() {
				query := string(baseRef.GetQueryInformations()[backend.GetQueryIdx()].GetNormalizedQuery())
				// // Skip backends with empty, semicolon-only, or pganalyze-collector queries
				if isQueryEmpty(query) {
					continue
				}
				backendKey.QueryFingerPrint = string(baseRef.GetQueryReferences()[backend.GetQueryIdx()].GetFingerprint())
			}
		}

		hash := backendKey.Hash()
		backendCounts[hash]++

		// Store first backend of each type for label creation
		if _, exists := firstBackendOfType[hash]; !exists {
			firstBackendOfType[hash] = &backendKey
		}
	}

	// Convert counts to time series
	var ts []prompb.TimeSeries
	for hash, count := range backendCounts {
		backendKey := firstBackendOfType[hash]

		labels := createLabelsForBackend(*backendKey, systemInfo)
		if labels == nil {
			continue // Skip this backend if labels is nil (empty query)
		}

		ts = append(ts, prompb.TimeSeries{
			Labels: labels,
			Samples: []prompb.Sample{{
				Timestamp: snapshotTimestamp,
				Value:     count,
			}},
		})
	}

	return ts
}

func createStaleMarkers(prevMetrics, currentMetrics []prompb.TimeSeries, timestamp int64) []prompb.TimeSeries {
	var staleMarkers []prompb.TimeSeries
	currentMetricsMap := make(map[string]bool)

	for _, metric := range currentMetrics {
		key := getMetricKey(metric)
		currentMetricsMap[key] = true
	}

	for _, prevMetric := range prevMetrics {
		key := getMetricKey(prevMetric)
		if !currentMetricsMap[key] {
			staleMarker := prompb.TimeSeries{
				Labels: prevMetric.Labels,
				Samples: []prompb.Sample{
					{
						Timestamp: timestamp,
						Value:     math.Float64frombits(value.StaleNaN), // NaN
					},
				},
			}
			staleMarkers = append(staleMarkers, staleMarker)
		}
	}

	return staleMarkers
}

func getMetricKey(metric prompb.TimeSeries) string {
	var labelPairs []string
	for _, label := range metric.Labels {
		if len(label.Value) != 0 {
			labelPairs = append(labelPairs, fmt.Sprintf("%s=%s", label.Name, label.Value))
		}
	}
	sort.Strings(labelPairs)
	return strings.Join(labelPairs, ",")
}

// Helper function to sort labels by name
func sortLabels(labels []prompb.Label) {
	sort.Slice(labels, func(i, j int) bool {
		return labels[i].Name < labels[j].Name
	})
}

func filter[T any](ss []T, test func(T) bool) (ret []T) {
	for _, s := range ss {
		if test(s) {
			ret = append(ret, s)
		}
	}
	return
}

func nonEmptyValFilter(l prompb.Label) bool {
	return len(l.Value) != 0
}

func isQueryEmpty(query string) bool {
	if query == "" ||
		query == ";" ||
		strings.HasPrefix(query, "/* pganalyze-collector */") {
		return true
	}
	return false
}
