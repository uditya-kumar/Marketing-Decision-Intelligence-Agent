"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from mdia.models.entities import DimAdSet, DimCampaign, DimChannel, DimCreative
from mdia.models.facts import FactAdDaily, FactStoreDaily, FactWebDaily
from mdia.models.ingestion import IngestionRun
from mdia.models.settings import BusinessSettings

__all__ = [
    "BusinessSettings",
    "DimAdSet",
    "DimCampaign",
    "DimChannel",
    "DimCreative",
    "FactAdDaily",
    "FactStoreDaily",
    "FactWebDaily",
    "IngestionRun",
]
