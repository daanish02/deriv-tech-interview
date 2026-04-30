# Post-Mortem: Database Connection Pool Exhaustion from Unindexed Batch Job

**Incident ID:** incident_b

## Incident Summary

On April 5, 2024, the order submission service experienced a complete outage for 13.33 minutes due to database connection pool exhaustion. The `open_orders_settlement` batch job, scheduled daily at 09:30 UTC, performed a full table scan on the `open_orders` table due to a missing composite index on `(account_id, order_date)`. Query `q_9031` ran for 748 seconds, exhausting all 100 database connections and triggering circuit breaker activation at the api-gateway, resulting in zero order processing capability during peak business hours.

## Timeline

- **09:44:22 UTC** — order-service detected slow database query `q_9031` with 1800ms duration
- **09:44:55 UTC** — db-primary connection pool exhausted: 100/100 connections in use, 39 requests waiting
- **09:45:10 UTC** — api-gateway began experiencing upstream timeouts to order-service
- **09:45:28 UTC** — api-gateway circuit breaker opened for order-service
- **09:45:40 UTC** — Complete order submission outage declared (SEV1)
- **09:57:14 UTC** — Query `q_9031` manually terminated after 748 seconds on `open_orders` table
- **09:57:15 UTC** — db-primary connection pool began releasing connections
- **09:59:00 UTC** — Order submission service fully restored
- **10:15:00 UTC** — Root cause identified: `open_orders_settlement` batch job scheduled at 09:30 UTC
- **10:15:01 UTC** — Missing composite index on `open_orders(account_id, order_date)` confirmed

## Root Cause

The `open_orders_settlement` batch job, scheduled to run daily at 09:30 UTC, executed query `q_9031` against the `open_orders` table without a composite index on `(account_id, order_date)`. This forced a full table scan that consumed a database connection for 748 seconds. As the query held its connection, subsequent order-service requests queued for available connections from the 100-connection pool. Within 33 seconds of pool exhaustion, all connections were consumed, causing order-service to timeout and triggering the api-gateway circuit breaker. The lack of query timeout enforcement on batch jobs allowed the problematic query to run unchecked until manual intervention.

## Contributing Factors

- Missing composite index on `open_orders(account_id, order_date)` forcing full table scans
- `open_orders_settlement` batch job scheduled at 09:30 UTC during peak business hours
- No query timeout limits configured for batch job queries on db-primary
- Database connection pool size of 100 insufficient to isolate batch job impact from real-time traffic
- No resource isolation between `open_orders_settlement` batch processing and order-service real-time queries
- Lack of query performance testing in pre-production environments for batch jobs
- No connection pool monitoring alerts configured before exhaustion threshold

## Severity Classification

**SEV1** — Complete loss of order submission capability for 13.33 minutes during business hours, resulting in zero revenue processing and direct customer impact with no degraded-mode fallback available.

## Action Items

| Priority | Title | Component | Owner | Category |
|----------|-------|-----------|-------|----------|
| P0 | Create composite index on `open_orders(account_id, order_date)` in production db-primary | db-primary | Database Team | Prevention |
| P0 | Implement 60-second query timeout for all `open_orders_settlement` batch job queries | open_orders_settlement | Batch Jobs Team | Prevention |
| P0 | Reschedule `open_orders_settlement` job from 09:30 UTC to 02:00 UTC (off-peak) | open_orders_settlement | Platform Team | Prevention |
| P1 | Add connection pool exhaustion alert at 80% threshold (80/100 connections) for db-primary | db-primary | Observability Team | Detection |
| P1 | Implement separate connection pool for batch jobs (20 connections) isolated from order-service pool (80 connections) | db-primary, order-service | Database Team | Prevention |
| P2 | Add query execution plan analysis to CI/CD pipeline for all queries against `open_orders` table | CI/CD Pipeline | Engineering Team | Prevention |
| P2 | Create runbook for connection pool exhaustion incidents referencing query termination procedure for `q_9031`-type scenarios | Runbooks | SRE Team | Response |

## Recurrence Risk

- **HIGH** — This is the third connection pool exhaustion incident in 12 months (INC-2023-041, INC-2024-007, incident_b), indicating systemic issues with batch job resource management and index maintenance. Without the P0 index creation and job rescheduling, the `open_orders_settlement` job will continue causing daily outages as the `open_orders` table grows.
- **MODERATE** — Even with the composite index, other batch jobs may have similar unindexed queries. The lack of query timeout enforcement and resource isolation means any future batch job could exhaust the shared connection pool during business hours.
- **CRITICAL BUSINESS IMPACT** — Each recurrence results in complete order processing outage. Historical data shows MTTR improving (31min → 22min → 13min) but business impact remains total revenue loss during incident window, with customer trust degradation from repeated failures.