"""
RemAgent: Autonomous Zero-Vector Memory Framework for AI Agents.
Powered by Google Gemini and biological sleep/REM consolidation principles.
"""

from remagent.schemas import (
    Fact,
    OperationalRule,
    DreamConsolidationResult,
    RawTurnLog,
    MemoryProfile,
    ContradictionResolution,
)
from remagent.storage.base import StorageAdapter
from remagent.storage.sqlite import SQLiteStorageAdapter
from remagent.storage.firestore import FirestoreStorageAdapter
from remagent.engine.synthesizer import DreamSynthesizer
from remagent.daemon import DreamDaemon
from remagent.governor import TokenBudgetGovernor
from remagent.decay import MemoryDecayEngine
from remagent.integrations.hermes import HermesMemoryConnector, RemAgentTool

__version__ = "1.0.0"
__all__ = [
    "Fact",
    "OperationalRule",
    "DreamConsolidationResult",
    "RawTurnLog",
    "MemoryProfile",
    "ContradictionResolution",
    "StorageAdapter",
    "SQLiteStorageAdapter",
    "FirestoreStorageAdapter",
    "DreamSynthesizer",
    "DreamDaemon",
    "TokenBudgetGovernor",
    "MemoryDecayEngine",
    "HermesMemoryConnector",
    "RemAgentTool",
]
