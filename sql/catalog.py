from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from sql.errors import SqlErrorCode, SqlServiceError
from sql.models import SemanticColumn, SemanticContext, SemanticView


class SemanticCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "SemanticCatalog":
        return cls(source=json.loads(path.read_text(encoding="utf-8")))

    def for_profile(self, profile: str) -> SemanticContext:
        profiles = set(self.source["profiles"])
        if profile not in profiles:
            raise SqlServiceError(
                SqlErrorCode.NOT_AUTHORIZED,
                "Le profil authentifié ne permet pas cet accès.",
            )

        views: dict[str, SemanticView] = {}
        for raw_view in self.source["views"]:
            if profile not in raw_view["profiles"]:
                continue
            columns = {
                name: SemanticColumn(name=name, **definition)
                for name, definition in raw_view["columns"].items()
            }
            views[raw_view["name"]] = SemanticView(
                name=raw_view["name"],
                description=raw_view["description"],
                columns=columns,
            )

        relations = tuple(
            {key: value for key, value in relation.items() if key != "profiles"}
            for relation in self.source.get("relations", [])
            if profile in relation["profiles"]
            and relation["left_view"] in views
            and relation["right_view"] in views
        )
        kpis = {
            item["name"]: item["definition"]
            for item in self.source.get("kpis", [])
            if profile in item["profiles"]
        }
        examples = tuple(
            {key: value for key, value in item.items() if key != "profiles"}
            for item in self.source.get("examples", [])
            if profile in item["profiles"]
        )

        versions = self.source["versions"]
        return SemanticContext(
            profile=profile,
            dataset_version=versions["dataset_version"],
            data_as_of=versions["data_as_of"],
            semantic_schema_version=versions["semantic_schema_version"],
            policy_version=versions["policy_version"],
            views=views,
            relations=relations,
            kpis=kpis,
            ambiguities=self.source.get("ambiguities", {}),
            examples=examples,
        )
