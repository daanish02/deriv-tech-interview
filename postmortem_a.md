# Post-Mortem: Trading Platform Outage Due to Batch Job Database Index Miss

**Incident ID:** incident_a

## Executive Summary

On March 15, 2024, the trading platform experienced a complete outage lasting 15.6 minutes due to database connection pool exhaustion. A daily batch job (`user_positions_recalc`) scheduled at 14:00 UTC performed a 731-second full table scan on the `user_positions` table due to a missing composite index on `(user_id, position_date)`, monopolizing database connections and cascading to pricing service failure. The incident resulted in a complete trading halt during peak hours, impacting all customer trading activity.

## Impact

**Duration:** 15.6 minutes (14:11:10 UTC - 14:26:45 UTC)  
**Severity:** Critical - Complete trading platform outage with 100% loss of trading functionality. All price quotes unavailable, preventing customers from executing trades during peak trading hours.

## Timeline Summary

- **14:08:44** - API gateway p99 latency degraded to 340ms (2.8x baseline)
- **14:09:01** - Pricing service slow queries detected (2.1s duration)
- **14:10:33** - Database connection pool exhausted (100/100 used, 47 waiting)
- **14:10:45** - Pricing service timeouts triggered at api-gateway
- **14:11:02** - Circuit breaker opened for pricing-service
- **14:11:10** - **Complete trading halt initiated** (critical business impact)
- **14:11:45** - PagerDuty alert triggered, engineer notified
- **14:16:30** - Engineer acknowledged (4m 45s response time)
- **14:22:08** - Long-running query killed (query_id=q_4489, 731s duration)
- **14:22:09** - Connection pool began recovery (47→12 waiting connections)
- **14:25:30** - Circuit breaker closed, pricing-service recovered
- **14:26:45** - **Trading resumed, full recovery achieved**
- **14:45:00** - Root cause confirmed: missing index on `user_positions(user_id, position_date)`

## Root Cause

The daily `user_positions_recalc` batch job, scheduled at 14:00 UTC during peak trading hours, executed a query against the `user_positions` table without a required composite index on `(user_id, position_date)`. This caused a full table scan lasting 731 seconds that monopolized database connections from the connection pool (100 max). As the pool exhausted with 47 connections queued, the pricing-service could not obtain database connections to serve real-time price quotes, triggering timeouts, circuit breaker activation, and ultimately a complete trading halt. The lack of query timeouts for batch jobs and absence of workload isolation between batch and real-time services allowed this single query to cascade into platform-wide failure.

## Contributing Factors

- Missing composite index on `user_positions(user_id, position_date)` causing full table scan
- Batch job scheduled during peak trading hours (14:00 UTC) without consideration for trading impact
- No query timeout limits configured for batch workloads
- Database connection pool size (100) insufficient to absorb long-running query impact
- Lack of workload isolation between batch jobs and critical real-time trading services
- No pre-production query performance validation or EXPLAIN plan analysis
- Similar incidents occurred previously (INC-2024-007, INC-2023-041) indicating pattern not addressed

## Action Items

| Priority | Title | Component | Owner | Category |
|----------|-------|-----------|-------|----------|
| P0 | Add composite index on `user_positions(user_id, position_date)` and validate query performance | db-primary | Database Team | Prevention |
| P0 | Implement mandatory query timeouts for all batch jobs (max 60s) | user_positions_recalc, batch-framework | Backend Team | Prevention |
| P1 | Reschedule `user_positions_recalc` to off-peak hours (02:00 UTC) with trading calendar awareness | batch-scheduler | Platform Team | Prevention |
| P1 | Implement separate connection pools for batch vs. real-time workloads with resource limits | db-primary | Database Team | Prevention |
| P2 | Add automated EXPLAIN plan analysis to CI/CD pipeline for query performance validation | ci-cd-pipeline | DevOps Team | Detection |
| P2 | Implement proactive alerting on connection pool utilization >70% with 2-minute threshold | monitoring | SRE Team | Detection |
| P3 | Conduct review of all batch jobs for missing indexes and schedule conflicts with trading hours | all-batch-jobs | Database Team | Prevention |

## Lessons Learned

- **Early warning signals existed but were not actionable**: Latency degradation was visible 6 minutes before critical failure (p99: 120ms→340ms), but no automated response prevented escalation to outage.
- **Circuit breaker pattern successfully limited blast radius**: While the circuit breaker couldn't prevent the outage, it prevented cascading failures and enabled faster recovery by failing fast once pricing-service became unavailable.
- **Recurring pattern not addressed**: This is the third similar incident (INC-2024-007, INC-2023-041) involving batch jobs and database resource contention, indicating systemic gaps in batch workload management and index governance that require architectural remediation beyond point fixes.