from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from .models import DnsRecordSpec

logger = logging.getLogger(__name__)


class DnsProvider(ABC):
    """
    DNS provider interface.
    MVP: only supports upsert (create/update).
    """

    @abstractmethod
    def upsert_record(self, record: DnsRecordSpec) -> None:
        """
        Create or update a DNS record so that it matches `record`.
        """
        raise NotImplementedError


class MockProvider(DnsProvider):
    """
    Fake provider that just logs what it *would* do.
    Useful for development and tests.
    """

    def upsert_record(self, record: DnsRecordSpec) -> None:
        logger.info(
            "[MockProvider] Would UPSERT %s %s (TTL=%s) values=%s in zone=%s",
            record.type,
            record.name,
            record.ttl,
            record.values,
            record.zone_id,
        )


class Route53Provider(DnsProvider):
    """
    Real provider that talks to AWS Route53 via boto3.
    Only used if you run with --provider route53 and have AWS credentials set.
    """

    def __init__(self, boto3_client) -> None:
        self._client = boto3_client

    def upsert_record(self, record: DnsRecordSpec) -> None:
        change_batch = {
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record.name,
                        "Type": record.type,
                        "TTL": record.ttl,
                        "ResourceRecords": [{"Value": v} for v in record.values],
                    },
                }
            ]
        }

        logger.info(
            "[Route53Provider] UPSERT %s %s (TTL=%s) values=%s in zone=%s",
            record.type,
            record.name,
            record.ttl,
            record.values,
            record.zone_id,
        )

        self._client.change_resource_record_sets(
            HostedZoneId=record.zone_id,
            ChangeBatch=change_batch,
        )
