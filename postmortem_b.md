# Post-Mortem: Database Connection Pool Exhaustion from Unindexed Batch Job

**Incident ID:** incident_b

## Executive Summary

On April 5, 2024, at 09:45:40 UTC, the order submission service experienced a complete outage lasting 13.33 minutes due to database connection pool exhaustion. A daily batch job (`open_orders_settlement`) scheduled at 09:30 UTC performed a full table scan on the `open_orders` table due to a missing composite index on `(account_id, order_date)`, causing a 748-second query that consumed all available database connections. The circuit breaker pattern successfully prevented cascading failures, and service was restored by terminating the long-running query.

## Impact

Order submission was completely unavailable for 13.33 minutes during business hours (09:45:40 - 09:59:00 UTC). All customer order placement attempts failed during this window, with the api-gateway circuit breaker preventing requests from reaching the degraded order-service.

## Timeline Summary

- **09:44:22** - Slow database query detected (query_id=q_9031, 1800ms duration)
- **09:44:55** - Database connection pool exhausted (100/100 connections, 39 waiting)
- **09:45:10** - API gateway experiencing upstream timeouts to order-service
- **09:45:28** - Circuit breaker opened for order-service
- **09:45:40** - Complete order submission outage declared
- **09:57:14** - Long-running query terminated (query_id=q_9031, 748s total duration)
- **09:57:15** - Connection pool recovery initiated
- **09:59:00** - Full service restoration achieved
- **10:15:00** - Root cause identified: `open_orders_settlement` batch job
- **10:15:01** - Missing index on `open_orders(account_id, order_date)` confirmed

## Root Cause

The daily `open_orders_settlement` batch job, scheduled at 09:30 UTC during business hours, executed a query against the `open_orders` table without a composite index on `(account_id, order_date)`. This forced a full table scan that ran for 748 seconds, holding database connections and exhausting the connection pool (100 connections with 39 queued). The connection starvation cascaded to the order-service, causing timeouts that triggered the api-gateway circuit breaker and resulted in complete order submission failure.

## Contributing Factors

- Batch job scheduled during peak business hours (09:30 UTC) without resource isolation
- Missing composite database index on `open_orders(account_id, order_date)` causing full table scans
- No query timeout limits configured for batch job queries
- Database connection pool size (100) lacked headroom for long-running operations
- Insufficient pre-production query performance testing for batch jobs
- No dedicated connection pool or read replica for batch processing workloads
- Third occurrence of similar root cause (INC-2024-007, INC-2023-041) indicating systemic issue

## Action Items

| Priority | Title | Component | Owner | Category |
|----------|-------|-----------|-------|----------|
| P0 | Add composite index on `open_orders(account_id, order_date)` | db-primary | Database Team | Prevention |
| P0 | Implement query timeout limits (60s) for all batch job queries | open_orders_settlement | Backend Team | Prevention |
| P1 | Reschedule `open_orders_settlement` batch job to off-peak hours (02:00 UTC) | batch-scheduler | Platform Team | Prevention |
| P1 | Create dedicated read replica and connection pool for batch processing | db-infrastructure | Database Team | Prevention |
| P2 | Implement automated query plan analysis in CI/CD for schema changes | ci-pipeline | Database Team | Detection |
| P2 | Add connection pool utilization alerting at 70% threshold | db-primary | Observability Team | Detection |
| P3 | Conduct audit of all batch jobs for missing indexes and scheduling conflicts | batch-jobs | Database Team | Prevention |

## Lessons Learned

- Circuit breaker pattern effectively prevented cascading failures and contained the blast radius to order-service
- This is the third incident with `missing_index_batch_job` root cause, indicating need for systematic query performance validation in development lifecycle
- Connection pool exhaustion incidents (13.33 min MTTR) resolve faster than previous similar incidents (INC-2024-007: 31 min) due to improved runbook procedures