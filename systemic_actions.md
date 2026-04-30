# Systemic Actions — Cross-Incident Analysis

## Overview
Analyzed action items across 2 incidents.
Found 4 systemic action groups.

## Systemic Issues (Shared Across Incidents)

### 1. Db-Primary
**Affected incidents:** incident_a, incident_b

- **[P0]** Add composite index on `user_positions(user_id, position_date)` and validate query performance
  - Add composite index on `user_positions(user_id, position_date)` and validate query performance
- **[P1]** Implement separate connection pools for batch vs. real-time workloads with resource limits
  - Implement separate connection pools for batch vs. real-time workloads with resource limits
- **[P0]** Add composite index on `open_orders(account_id, order_date)`
  - Add composite index on `open_orders(account_id, order_date)`
- **[P2]** Add connection pool utilization alerting at 70% threshold
  - Add connection pool utilization alerting at 70% threshold

### 2. Batch-Scheduler
**Affected incidents:** incident_a, incident_b

- **[P1]** Reschedule `user_positions_recalc` to off-peak hours (02:00 UTC) with trading calendar awareness
  - Reschedule `user_positions_recalc` to off-peak hours (02:00 UTC) with trading calendar awareness
- **[P1]** Reschedule `open_orders_settlement` batch job to off-peak hours (02:00 UTC)
  - Reschedule `open_orders_settlement` batch job to off-peak hours (02:00 UTC)

### 3. Prevention
**Affected incidents:** incident_a, incident_b

- **[P0]** Implement mandatory query timeouts for all batch jobs (max 60s)
  - Implement mandatory query timeouts for all batch jobs (max 60s)
- **[P3]** Conduct review of all batch jobs for missing indexes and schedule conflicts with trading hours
  - Conduct review of all batch jobs for missing indexes and schedule conflicts with trading hours
- **[P0]** Implement query timeout limits (60s) for all batch job queries
  - Implement query timeout limits (60s) for all batch job queries
- **[P1]** Create dedicated read replica and connection pool for batch processing
  - Create dedicated read replica and connection pool for batch processing
- **[P3]** Conduct audit of all batch jobs for missing indexes and scheduling conflicts
  - Conduct audit of all batch jobs for missing indexes and scheduling conflicts

### 4. Detection
**Affected incidents:** incident_a, incident_b

- **[P2]** Add automated EXPLAIN plan analysis to CI/CD pipeline for query performance validation
  - Add automated EXPLAIN plan analysis to CI/CD pipeline for query performance validation
- **[P2]** Implement proactive alerting on connection pool utilization >70% with 2-minute threshold
  - Implement proactive alerting on connection pool utilization >70% with 2-minute threshold
- **[P2]** Implement automated query plan analysis in CI/CD for schema changes
  - Implement automated query plan analysis in CI/CD for schema changes

## All Action Items by Incident

### incident_a
- **[P0]** Add composite index on `user_positions(user_id, position_date)` and validate query performance (db-primary)
- **[P0]** Implement mandatory query timeouts for all batch jobs (max 60s) (user_positions_recalc, batch-framework)
- **[P1]** Reschedule `user_positions_recalc` to off-peak hours (02:00 UTC) with trading calendar awareness (batch-scheduler)
- **[P1]** Implement separate connection pools for batch vs. real-time workloads with resource limits (db-primary)
- **[P2]** Add automated EXPLAIN plan analysis to CI/CD pipeline for query performance validation (ci-cd-pipeline)
- **[P2]** Implement proactive alerting on connection pool utilization >70% with 2-minute threshold (monitoring)
- **[P3]** Conduct review of all batch jobs for missing indexes and schedule conflicts with trading hours (all-batch-jobs)

### incident_b
- **[P0]** Add composite index on `open_orders(account_id, order_date)` (db-primary)
- **[P0]** Implement query timeout limits (60s) for all batch job queries (open_orders_settlement)
- **[P1]** Reschedule `open_orders_settlement` batch job to off-peak hours (02:00 UTC) (batch-scheduler)
- **[P1]** Create dedicated read replica and connection pool for batch processing (db-infrastructure)
- **[P2]** Implement automated query plan analysis in CI/CD for schema changes (ci-pipeline)
- **[P2]** Add connection pool utilization alerting at 70% threshold (db-primary)
- **[P3]** Conduct audit of all batch jobs for missing indexes and scheduling conflicts (batch-jobs)

