# src/models/__init__.py
from .UserWeb import UserWeb
from .TaxonRef import TaxonRef
from .Party import EventParty, MediaParty, OccurrenceParty, Party, TaxonParty
from .ScientificSource import ScientificSource
from .ScientificTaxonLink import ScientificTaxonLink
from .ScientificUse import ScientificUse
from .ScientificEcology import ScientificEcology
from .EthnoSource import EthnoSource
from .EthnoTaxonKnowledge import EthnoTaxonKnowledge
from .EthnoUse import EthnoUse

__all__ = [
    "UserWeb",
    "TaxonRef",
    "Party",
    "TaxonParty",
    "EventParty",
    "OccurrenceParty",
    "MediaParty",
    "ScientificSource",
    "ScientificTaxonLink",
    "ScientificUse",
    "ScientificEcology",
    "EthnoSource",
    "EthnoTaxonKnowledge",
    "EthnoUse",
]
