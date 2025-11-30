from __future__ import annotations

import argparse
import logging

from pymongo import MongoClient

from .planner import apply_config_file
from .queue import JobQueue
from .providers import MockProvider, Route53Provider, DnsProvider
from .executor import start_dispatchers


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_provider(name: str) -> DnsProvider:
    if name == "mock":
        return MockProvider()
    if name == "route53":
        import boto3

        client = boto3.client("route53")
        return Route53Provider(client)
    raise ValueError(f"Unknown provider: {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DNS provisioning job queue with MongoDB",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to DNS record YAML config",
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI (default: mongodb://localhost:27017)",
    )
    parser.add_argument(
        "--mongo-db",
        default="dns_control_plane",
        help="MongoDB database name (default: dns_control_plane)",
    )
    parser.add_argument(
        "--mongo-collection",
        default="dns_records",
        help="MongoDB collection name (default: dns_records)",
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "route53"],
        default="mock",
        help="DNS provider backend (default: mock)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of dispatcher threads (default: 1)",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.mongo_db]
    coll = db[args.mongo_collection]

    provider = get_provider(args.provider)
    queue = JobQueue()

    # Start dispatcher threads
    start_dispatchers(coll, provider, queue, workers=args.workers)

    # Planner-style apply: read config, write Mongo, enqueue reconcile jobs
    logger.info("Applying config from %s", args.config)
    apply_config_file(coll, queue, args.config)

    # Block until all jobs processed
    queue.join()
    logger.info("All jobs processed; exiting.")


if __name__ == "__main__":
    main()
