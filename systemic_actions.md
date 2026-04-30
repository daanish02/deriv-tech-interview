# Systemic Actions — Cross-Incident Analysis

## Overview
Analyzed action items across 2 incidents.
Found 3 systemic action groups.

## Systemic Issues (Shared Across Incidents)

### 1. Prevention
**Affected incidents:** incident_a, incident_b

- **[P0]** Add composite index on user_positions(user_id, position_date) and validate query plan for user_positions_recalc batch job
  - Add composite index on user_positions(user_id, position_date) and validate query plan for user_positions_recalc batch job
- **[P0]** Reschedule user_positions_recalc batch job to 02:00 UTC (off-peak hours) and implement maintenance window policy for all batch jobs
  - Reschedule user_positions_recalc batch job to 02:00 UTC (off-peak hours) and implement maintenance window policy for all batch jobs
- **[P0]** Implement 60-second query timeout for all batch jobs accessing db-primary
  - Implement 60-second query timeout for all batch jobs accessing db-primary
- **[P1]** Create dedicated read replica (db-batch-replica) for batch workloads and migrate user_positions_recalc to isolated connection pool
  - Create dedicated read replica (db-batch-replica) for batch workloads and migrate user_positions_recalc to isolated connection pool
- **[P2]** Implement mandatory EXPLAIN analysis and query performance testing in CI/CD pipeline for all queries against user_positions, transactions, and orders tables
  - Implement mandatory EXPLAIN analysis and query performance testing in CI/CD pipeline for all queries against user_positions, transactions, and orders tables
- **[P0]** Create composite index on `open_orders(account_id, order_date)` in production db-primary
  - Create composite index on `open_orders(account_id, order_date)` in production db-primary
- **[P0]** Implement 60-second query timeout for all `open_orders_settlement` batch job queries
  - Implement 60-second query timeout for all `open_orders_settlement` batch job queries
- **[P0]** Reschedule `open_orders_settlement` job from 09:30 UTC to 02:00 UTC (off-peak)
  - Reschedule `open_orders_settlement` job from 09:30 UTC to 02:00 UTC (off-peak)
- **[P1]** Implement separate connection pool for batch jobs (20 connections) isolated from order-service pool (80 connections)
  - Implement separate connection pool for batch jobs (20 connections) isolated from order-service pool (80 connections)
- **[P2]** Add query execution plan analysis to CI/CD pipeline for all queries against `open_orders` table
  - Add query execution plan analysis to CI/CD pipeline for all queries against `open_orders` table

### 2. Detection
**Affected incidents:** incident_a, incident_b

- **[P1]** Add alerting on db-primary connection pool utilization >70% and query duration >10s for user_positions table
  - Add alerting on db-primary connection pool utilization >70% and query duration >10s for user_positions table
- **[P1]** Add connection pool exhaustion alert at 80% threshold (80/100 connections) for db-primary
  - Add connection pool exhaustion alert at 80% threshold (80/100 connections) for db-primary

### 3. Response
**Affected incidents:** incident_a, incident_b

- **[P2]** Create runbook for pricing-service circuit breaker incidents with automated query kill procedure for db-primary queries >60s
  - Create runbook for pricing-service circuit breaker incidents with automated query kill procedure for db-primary queries >60s
- **[P2]** Create runbook for connection pool exhaustion incidents referencing query termination procedure for `q_9031`-type scenarios
  - Create runbook for connection pool exhaustion incidents referencing query termination procedure for `q_9031`-type scenarios

## All Action Items by Incident

### incident_a
- **[P0]** Add composite index on user_positions(user_id, position_date) and validate query plan for user_positions_recalc batch job (db-primary, user_positions_recalc)
- **[P0]** Reschedule user_positions_recalc batch job to 02:00 UTC (off-peak hours) and implement maintenance window policy for all batch jobs (user_positions_recalc)
- **[P0]** Implement 60-second query timeout for all batch jobs accessing db-primary (db-primary, user_positions_recalc)
- **[P1]** Create dedicated read replica (db-batch-replica) for batch workloads and migrate user_positions_recalc to isolated connection pool (db-primary, user_positions_recalc)
- **[P1]** Add alerting on db-primary connection pool utilization >70% and query duration >10s for user_positions table (db-primary, monitoring)
- **[P2]** Implement mandatory EXPLAIN analysis and query performance testing in CI/CD pipeline for all queries against user_positions, transactions, and orders tables (CI/CD, Database Team)
- **[P2]** Create runbook for pricing-service circuit breaker incidents with automated query kill procedure for db-primary queries >60s (pricing-service, api-gateway, db-primary)

### incident_b
- **[P0]** Create composite index on `open_orders(account_id, order_date)` in production db-primary (db-primary)
- **[P0]** Implement 60-second query timeout for all `open_orders_settlement` batch job queries (open_orders_settlement)
- **[P0]** Reschedule `open_orders_settlement` job from 09:30 UTC to 02:00 UTC (off-peak) (open_orders_settlement)
- **[P1]** Add connection pool exhaustion alert at 80% threshold (80/100 connections) for db-primary (db-primary)
- **[P1]** Implement separate connection pool for batch jobs (20 connections) isolated from order-service pool (80 connections) (db-primary, order-service)
- **[P2]** Add query execution plan analysis to CI/CD pipeline for all queries against `open_orders` table (CI/CD Pipeline)
- **[P2]** Create runbook for connection pool exhaustion incidents referencing query termination procedure for `q_9031`-type scenarios (Runbooks)

