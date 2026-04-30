# Post-Mortem: Trading Platform Outage Due to Batch Job Database Index Missing

**Incident ID:** incident_a

## Incident Summary

On March 15, 2024, the trading platform experienced a complete outage for 15.6 minutes (14:11-14:26 UTC) during peak trading hours. The daily `user_positions_recalc` batch job, scheduled at 14:00 UTC, performed a 731-second full table scan on the `user_positions` table due to a missing composite index on `(user_id, position_date)`, exhausting the database connection pool and cascading to pricing-service failure. All trading activity was halted as the platform could not serve price quotes, resulting in significant business impact during active market hours.

## Timeline

- **14:08:44 UTC** — api-gateway p99 latency degraded from 120ms baseline to 340ms (2.8x increase)
- **14:09:01 UTC** — pricing-service slow query detected (query_id=q_4821, duration=2100ms)
- **14:09:15 UTC** — Additional slow queries in pricing-service (query_id=q_4822, duration=3400ms)
- **14:10:33 UTC** — db-primary connection pool exhausted (100/100 connections, 47 waiting)
- **14:10:45 UTC** — api-gateway timeout to pricing-service (5000ms timeout exceeded)
- **14:11:02 UTC** — Circuit breaker opened for pricing-service
- **14:11:10 UTC** — **CRITICAL: Complete trading halt initiated** — unable to serve price quotes
- **14:11:45 UTC** — PagerDuty alert triggered, engineer notified
- **14:16:30 UTC** — Engineer acknowledged (4m 45s response time)
- **14:22:08 UTC** — Long-running query killed (query_id=q_4489, duration=731s, table=user_positions from user_positions_recalc batch job)
- **14:22:09 UTC** — Connection pool recovery began (waiting connections: 47→12)
- **14:23:15 UTC** — pricing-service query latency normalized
- **14:25:30 UTC** — Circuit breaker closed, pricing-service recovered
- **14:26:45 UTC** — Trading platform fully restored
- **14:45:00 UTC** — Root cause confirmed: user_positions_recalc batch job scheduled daily at 14:00 UTC
- **14:45:01 UTC** — Missing index identified: user_positions table lacks composite index on (user_id, position_date)

## Root Cause

The `user_positions_recalc` batch job, scheduled daily at 14:00 UTC, executed query q_4489 against the `user_positions` table without a composite index on `(user_id, position_date)`. This forced a full table scan lasting 731 seconds, monopolizing database connections from the db-primary connection pool (sized at 100). As the long-running query held connections, the pricing-service's real-time queries began queuing, with 47 connections waiting by 14:10:33 UTC. This exhaustion cascaded to pricing-service timeouts, triggering the api-gateway circuit breaker and ultimately forcing a complete trading halt as the platform could not generate price quotes for customer trades.

## Contributing Factors

- **Batch job scheduled during peak trading hours** — user_positions_recalc runs at 14:00 UTC, coinciding with active market hours
- **Missing composite index on user_positions(user_id, position_date)** — forced full table scan for batch query q_4489
- **No query timeout enforcement for batch jobs** — 731-second query ran uninterrupted until manual intervention
- **Insufficient connection pool isolation** — db-primary pool (100 connections) shared between real-time trading services and batch workloads
- **Lack of pre-production query performance validation** — user_positions_recalc deployed without EXPLAIN analysis or load testing
- **No workload prioritization** — batch jobs competed equally with critical pricing-service queries for database resources
- **Historical pattern ignored** — similar incidents (INC-2024-007, INC-2023-041) involving batch jobs and missing indexes occurred previously

## Severity Classification

**SEV1** — Complete trading platform outage during peak market hours for 15.6 minutes, preventing all customer trading activity and price quote generation, with direct revenue impact and potential regulatory implications.

## Action Items

| Priority | Title | Component | Owner | Category |
|----------|-------|-----------|-------|----------|
| P0 | Add composite index on user_positions(user_id, position_date) and validate query plan for user_positions_recalc batch job | db-primary, user_positions_recalc | Database Team | Prevention |
| P0 | Reschedule user_positions_recalc batch job to 02:00 UTC (off-peak hours) and implement maintenance window policy for all batch jobs | user_positions_recalc | Data Engineering | Prevention |
| P0 | Implement 60-second query timeout for all batch jobs accessing db-primary | db-primary, user_positions_recalc | Database Team | Prevention |
| P1 | Create dedicated read replica (db-batch-replica) for batch workloads and migrate user_positions_recalc to isolated connection pool | db-primary, user_positions_recalc | Infrastructure Team | Prevention |
| P1 | Add alerting on db-primary connection pool utilization >70% and query duration >10s for user_positions table | db-primary, monitoring | SRE Team | Detection |
| P2 | Implement mandatory EXPLAIN analysis and query performance testing in CI/CD pipeline for all queries against user_positions, transactions, and orders tables | CI/CD, Database Team | Database Team | Prevention |
| P2 | Create runbook for pricing-service circuit breaker incidents with automated query kill procedure for db-primary queries >60s | pricing-service, api-gateway, db-primary | SRE Team | Response |

## Recurrence Risk

- **HIGH recurrence risk** — Three similar incidents (INC-2024-007, INC-2023-041, INC-2023-089) in the past 18 months indicate systemic issues with batch job scheduling, missing indexes, and connection pool management. Without dedicated batch infrastructure and pre-production query validation, additional tables (transactions, orders) remain vulnerable to similar full table scan scenarios.
- **CRITICAL business impact if recurring** — Trading platform outages during market hours result in direct revenue loss, customer trust erosion, and potential regulatory scrutiny. The 15.6-minute MTTR represents improvement over INC-2024-007 (31 minutes) but remains unacceptable for a financial trading platform.
- **Immediate mitigation required** — The P0 action items (index creation, job rescheduling, query timeouts) must be completed within 48 hours to prevent recurrence during the next user_positions_recalc execution at 14:00 UTC on March 16, 2024.