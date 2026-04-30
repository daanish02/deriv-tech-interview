# Incident A Communications

## Initial Notification

**URGENT: Trading Platform Outage**

We are currently experiencing a complete outage of our trading platform as of 14:00 UTC. Users are unable to access trading functions.

**Impact:** All trading operations are unavailable.

**Status:** Our engineering team is actively investigating the root cause. Database connectivity issues have been identified as the primary concern.

**Next Update:** We will provide an update within 30 minutes or sooner if the situation changes.

We apologize for the disruption and are working urgently to restore service.

---

## Status Update

**UPDATE: Trading Platform Outage - Investigation Ongoing**

**Time:** 14:10 UTC | **Duration:** 10 minutes

Our team has identified the root cause: a scheduled batch job is consuming all database connections, preventing normal trading operations.

**Current Actions:**
- Terminating the problematic batch job
- Restoring database connection availability
- Preparing to bring trading services back online

**Expected Resolution:** Within the next 10 minutes

We continue to work urgently on restoration. No data loss has occurred.

---

## Resolution Notice

**RESOLVED: Trading Platform Restored**

**Incident Duration:** 15.6 minutes (14:00 - 14:15:36 UTC)

Our trading platform has been fully restored. All services are operational.

**Root Cause:** A daily batch job caused database connection exhaustion due to a missing database index, blocking all trading operations.

**Resolution:** The batch job was terminated and database connections restored.

**Preventive Measures:**
- Database index has been added
- Enhanced monitoring implemented
- Batch job scheduling review underway

No trades or data were lost. We sincerely apologize for the disruption.

---

# Incident B Communications

## Initial Notification

**URGENT: Order Submission Service Outage**

We are experiencing a complete outage of our order submission service as of 09:45 UTC. Users cannot submit new orders.

**Impact:** Order submission unavailable. Existing positions and account access are unaffected.

**Status:** Our engineering team is investigating. Initial analysis indicates database connectivity issues similar to a previous incident.

**Next Update:** Within 30 minutes or when significant progress is made.

We understand the urgency and are prioritizing resolution.

---

## Status Update

**UPDATE: Order Submission Outage - Root Cause Identified**

**Time:** 09:55 UTC | **Duration:** 10 minutes

We have identified the cause: a scheduled settlement batch job is exhausting database connections due to a missing index.

**Current Actions:**
- Stopping the problematic batch job
- Restoring database connection pool
- Implementing immediate fix

**Expected Resolution:** Within 5-10 minutes

Market data and account viewing remain functional. Only order submission is affected.

---

## Resolution Notice

**RESOLVED: Order Submission Service Restored**

**Incident Duration:** 13.33 minutes (09:45:40 - 09:59 UTC)

Order submission service is fully operational.

**Root Cause:** The `open_orders_settlement` batch job caused database connection pool exhaustion due to a missing composite index.

**Resolution:** Batch job terminated, connections restored, and missing index added.

**Actions Taken:**
- Immediate database optimization
- Review of all batch job queries initiated
- Monitoring enhancements deployed

This represents a repeat incident pattern. We are conducting a comprehensive review of our batch processing architecture to prevent recurrence.

We apologize for the disruption to your trading activities.