# Incident A Communications

## User-Facing Status Page Update

### [Initial Notification]
**March 15, 2024 - 14:15 UTC**

We are currently investigating an issue affecting our trading platform. Users may be unable to access their accounts or place trades. Our team is actively working to restore full service.

### [Status Update]
**March 15, 2024 - 14:20 UTC**

We have identified the cause of the service disruption and are implementing a fix. Trading functionality remains unavailable. We understand the urgency during market hours and are prioritizing restoration of service.

### [Resolution Notice]
**March 15, 2024 - 14:30 UTC**

Service has been fully restored as of 14:26 UTC. All trading functions are now operational. The disruption lasted approximately 16 minutes during peak trading hours.

**What happened:** A scheduled maintenance process encountered an unexpected performance issue that temporarily prevented our systems from processing requests. We have resolved the immediate issue and are implementing additional safeguards to prevent recurrence.

**Your accounts:** All account data and positions remain secure and accurate. No trades or data were lost during this incident.

We sincerely apologize for the disruption during critical trading hours.

## Engineering Leadership Retrospective Summary

### [Summary]
**Duration:** 15.6 minutes (14:11-14:26 UTC, March 15, 2024)  
**MTTR:** 15.6 minutes  
**Impact:** Complete trading platform outage during peak hours

The `user_positions_recalc` batch job triggered a 731-second full table scan on the `user_positions` table due to a missing composite index on `(user_id, position_date)`, exhausting the database connection pool and blocking all trading operations.

### [Technical Root Cause]
The daily batch job scheduled at 14:00 UTC executed without the required composite index, causing query performance degradation from sub-second to 12+ minutes. The connection pool (max 50 connections) was fully consumed by the long-running query, starving the trading API of database connections.

### [Action Items Summary]
- **Database Team:** Create composite index on `user_positions(user_id, position_date)` - COMPLETED
- **Platform Team:** Implement connection pool isolation for batch jobs (separate pool with max 10 connections)
- **SRE Team:** Add query duration alerting (threshold: 30 seconds) for all batch jobs
- **Database Team:** Conduct index audit across all tables accessed by scheduled jobs

### [Recurrence Assessment]
**Risk Level:** Medium. Similar missing indexes may exist on other batch job queries. The index audit and connection pool isolation will significantly reduce recurrence probability within 2 weeks.

---

# Incident B Communications

## User-Facing Status Page Update

### [Initial Notification]
**April 5, 2024 - 09:35 UTC**

We are experiencing technical difficulties with order submission. You may be unable to place new orders at this time. Existing positions and account access are not affected. Our team is investigating.

### [Status Update]
**April 5, 2024 - 09:40 UTC**

We have identified the source of the issue and are working to restore order submission capability. Account viewing and position monitoring remain fully functional. We expect to resolve this shortly.

### [Resolution Notice]
**April 5, 2024 - 09:45 UTC**

Order submission has been fully restored as of 09:43 UTC. All order functions are now operating normally. The disruption lasted approximately 13 minutes.

**What happened:** A routine background process temporarily affected our order processing systems. We stopped the process and restored normal operations.

**Your orders:** Any orders placed during this window may have experienced delays but have been processed in the sequence received. All account balances and positions are accurate.

We apologize for any inconvenience this may have caused to your trading activities.

## Engineering Leadership Retrospective Summary

### [Summary]
**Duration:** 13.33 minutes (09:30-09:43 UTC, April 5, 2024)  
**MTTR:** 13.33 minutes  
**Impact:** Complete order submission service outage

The `open_orders_settlement` batch job executed a full table scan on the `open_orders` table due to a missing composite index on `(account_id, order_date)`. Query `q_9031` ran for 748 seconds, exhausting the connection pool and blocking all order submission requests.

### [Technical Root Cause]
The daily settlement job scheduled at 09:30 UTC performed an unindexed query against the `open_orders` table. The missing composite index caused a full table scan consuming all 50 available database connections, preventing the order submission service from acquiring connections to process new orders.

### [Action Items Summary]
- **Database Team:** Create composite index on `open_orders(account_id, order_date)` - COMPLETED
- **Order Services Team:** Implement dedicated connection pool for batch operations (max 8 connections)
- **Database Team:** Complete comprehensive index coverage analysis for all batch job queries by April 12
- **SRE Team:** Deploy circuit breaker pattern for batch jobs exceeding 60-second execution time
- **Platform Team:** Implement batch job execution window validation (prevent overlap with peak trading hours)

### [Recurrence Assessment]
**Risk Level:** Medium-High. This is the second connection pool exhaustion incident in three weeks, indicating systemic index management gaps. The comprehensive index audit and connection pool isolation strategy will address root causes. Estimated risk reduction to Low within 10 days post-audit completion.