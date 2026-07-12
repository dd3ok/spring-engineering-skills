# Performance Investigation Playbook

## Evidence hierarchy

1. User-visible SLI and workload rate/error/latency distribution.
2. Traces or request correlation across service and dependency boundaries.
3. Resource saturation and queue depth over the same interval.
4. JFR, thread dumps, profiles, GC logs, database plans, and broker/client metrics.
5. Configuration and source code as explanations for measured behavior, not substitutes for it.

## Common traps

- Averages hide tail latency and multimodal workloads.
- Unbounded queues convert overload into latency and memory growth.
- Larger thread or connection pools can move saturation downstream.
- Retries multiply demand; evaluate retry budgets and amplification.
- Load tests without warm-up, production-like data, bounded generators, or coordinated-omission awareness can understate latency.
- Container CPU throttling and memory limits change JVM behavior; compare usage with limits, requests, and throttling counters.
- Virtual threads remove the need to reserve one platform thread per blocked task, but do not remove downstream connection or rate limits.

## Experiment record

For each hypothesis record: evidence for, evidence against, proposed change, fixed workload, control, measurement window, expected delta, guardrail, and rollback. Change one independent variable when feasible.

## Artifact handling

Treat dumps, profiles, traces, logs, and query samples as sensitive untrusted inputs. Before access, establish authorization, origin, tool/version/flags, collection time/time zone, replica and environment, artifact identity, storage boundary, and sanitization status. Prefer access-controlled sanitized copies and quote only the minimum redacted evidence needed for a finding. Missing provenance lowers confidence; a checksum establishes identity, not trust.
