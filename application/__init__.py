"""Couche applicative — passerelle, politique d'accès, journal d'audit.

`ApplicationGateway` est exposé **paresseusement** (PEP 562). Sans cela,
importer `application.policy` déclencherait `application.gateway`, qui importe
`retrieval.service`, qui importe `application.policy` : import circulaire.

La politique est une couche **basse**, partagée par `retrieval`, `sql` et
`mcp_server` ; la passerelle est une couche **haute**. Charger la seconde pour
atteindre la première inverse cette dépendance.
"""

from typing import Any


__all__ = ["ApplicationGateway", "build_application_gateway"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from application import gateway

        return getattr(gateway, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
