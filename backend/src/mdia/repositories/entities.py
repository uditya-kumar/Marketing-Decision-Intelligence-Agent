"""Ad entity dimensions: upsert by platform ID and resolve surrogate keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, tuple_

from mdia.models import DimAdSet, DimCampaign, DimChannel, DimCreative
from mdia.repositories.upsert import upsert

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

# (parent id, platform external_id) → surrogate id of the child row.
type EntityIds = dict[tuple[Any, str], int]


class EntityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_channel(self, channel_id: str, name: str) -> None:
        upsert(self._session, DimChannel, [{"id": channel_id, "name": name}])

    def upsert_campaigns(self, rows: Sequence[dict[str, Any]]) -> EntityIds:
        """Rows carry ``channel_id, external_id, name, platform``."""
        return self._upsert_children(DimCampaign, "channel_id", rows)

    def upsert_ad_sets(self, rows: Sequence[dict[str, Any]]) -> EntityIds:
        """Rows carry ``campaign_id, external_id, name``."""
        return self._upsert_children(DimAdSet, "campaign_id", rows)

    def upsert_creatives(self, rows: Sequence[dict[str, Any]]) -> EntityIds:
        """Rows carry ``ad_set_id, external_id, name``."""
        return self._upsert_children(DimCreative, "ad_set_id", rows)

    def _upsert_children(
        self,
        model: type[DimCampaign | DimAdSet | DimCreative],
        parent: str,
        rows: Sequence[dict[str, Any]],
    ) -> EntityIds:
        """Upsert on ``(parent, external_id)`` and map each such pair to its row ID."""
        if not rows:
            return {}
        upsert(self._session, model, rows, key=(parent, "external_id"))
        parent_column = getattr(model, parent)
        found = self._session.execute(
            select(parent_column, model.external_id, model.id).where(
                tuple_(parent_column, model.external_id).in_(
                    [(row[parent], row["external_id"]) for row in rows]
                )
            )
        )
        return {(parent_id, external_id): id_ for parent_id, external_id, id_ in found}
