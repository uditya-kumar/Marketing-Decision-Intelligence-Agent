"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from mdia.models.entities import DimAdSet, DimCampaign, DimChannel, DimCreative
from mdia.models.facts import FactAdDaily, FactStoreDaily, FactWebDaily
from mdia.models.ingestion import IngestionRun

__all__ = [
    "DimAdSet",
    "DimCampaign",
    "DimChannel",
    "DimCreative",
    "FactAdDaily",
    "FactStoreDaily",
    "FactWebDaily",
    "IngestionRun",
]
