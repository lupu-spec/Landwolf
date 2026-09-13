from datetime import datetime, timezone


class IngestionService:
    """
    Provider-neutral ingestion boundary.

    Adapters should fetch raw records, normalize them to the canonical property
    schema, validate geometry/source metadata, and upsert by source parcel ID.
    """

    def __init__(self, registry):
        self.registry = registry

    def run(self, provider_name, **kwargs):
        provider = self.registry.get(provider_name)
        records = provider.fetch(**kwargs)
        return {
            "provider": provider_name,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "records": records,
        }
