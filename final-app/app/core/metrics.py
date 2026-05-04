"""Prometheus metrics (Module 21)."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


http_requests_total = Counter(
    "enrollment_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "enrollment_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

pipeline_runs_total = Counter(
    "enrollment_pipeline_runs_total",
    "Total pipeline runs",
    ["outcome"],
)

pipeline_duration_seconds = Histogram(
    "enrollment_pipeline_duration_seconds",
    "Pipeline duration",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

worker_queue_size = Gauge(
    "enrollment_worker_queue_size",
    "In-flight background jobs",
)

domain_errors_total = Counter(
    "enrollment_domain_errors_total",
    "Domain errors raised",
    ["code"],
)
