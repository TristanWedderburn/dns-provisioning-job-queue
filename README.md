# dns-provisioning-job-queue

A tiny control-plane style DNS provisioning MVP built with:

- **MongoDB** as the source of truth (`dns_records` collection)
- **Spec + Status** sub-objects per record
- An in-memory **job queue** and dispatcher loop
- A pluggable DNS provider (Mock by default, Route53 optional)

Flow:

> YAML config → Planner writes/updates Mongo `dns_records` (spec + desired state)  
> → enqueues reconcile jobs → Dispatcher reconciles each record via provider.

## Document shape (Mongo)

Each document in `dns_records` looks like:

```jsonc
{
  "_id": "ObjectId",
  "spec": {
    "zoneId": "Z123...",
    "name": "mongo.example.com",
    "type": "CNAME",
    "ttl": 60,
    "values": ["cluster-abc123.mongodb.net"],
    "desiredState": "PRESENT",
    "version": 3
  },
  "status": {
    "reconcileStatus": "PENDING",
    "observedVersion": 2,
    "lastError": "Some error or null",
    "lastReconciledAt": "2025-11-29T10:15:00Z"
  },
  "createdAt": "2025-11-28T09:00:00Z",
  "updatedAt": "2025-11-29T10:20:00Z"
}

## Running Locally

### Prerequisites
- install mongo
- install poetry and install packages with poetry

# Procedure
- run simulate.py script
