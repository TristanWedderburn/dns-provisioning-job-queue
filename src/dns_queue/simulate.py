from __future__ import annotations

import logging
from pprint import pprint

from pymongo import MongoClient

from .queue import JobQueue
from .providers import MockProvider
from .planner import apply_config_file
from .executor import start_dispatchers


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def print_dns_records(coll) -> None:
    logger.info("Current dns_records documents:")
    for doc in coll.find().sort("spec.name"):
        # Pretty-print a subset of fields to keep output readable
        pprint(
            {
                "_id": str(doc["_id"]),
                "spec": doc["spec"],
                "status": doc["status"],
                "createdAt": doc.get("createdAt"),
                "updatedAt": doc.get("updatedAt"),
            }
        )


def run_simulation() -> None:
    setup_logging()
    logger.info("Starting DNS control-plane simulation")

    # Connect to MongoDB (same defaults as main.py)
    mongo_uri = "mongodb://localhost:27017"
    db_name = "dns_control_plane"
    coll_name = "dns_records"

    client = MongoClient(mongo_uri)
    db = client[db_name]
    coll = db[coll_name]

    # Clean slate for simulation
    logger.info("Clearing collection %s.%s", db_name, coll_name)
    coll.delete_many({})

    # Use mock provider for simulation
    provider = MockProvider()
    queue = JobQueue()

    # Start dispatcher(s)
    start_dispatchers(coll, provider, queue, workers=1)

    # --- Phase 1: Apply initial config ---
    logger.info("=== Phase 1: Applying config/example-records.yaml ===")
    apply_config_file(coll, queue, "config/example-records.yaml")

    # Wait for all jobs to finish
    queue.join()

    logger.info("=== After Phase 1 reconciliation ===")
    print_dns_records(coll)

    # --- Phase 2: Apply updated config (v2) ---
    logger.info("=== Phase 2: Applying config/example-records-v2.yaml ===")
    apply_config_file(coll, queue, "config/example-records-v2.yaml")

    # Wait for all jobs again
    queue.join()

    logger.info("=== After Phase 2 reconciliation ===")
    print_dns_records(coll)

    logger.info("Simulation complete.")


if __name__ == "__main__":
    run_simulation()
