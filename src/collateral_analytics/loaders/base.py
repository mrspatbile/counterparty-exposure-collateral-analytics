"""Abstract base class for data loaders."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class BaseDataLoader(ABC, Generic[T]):
    """Abstract base class for loading domain objects from data sources.

    Subclasses must implement load() to read data and return domain objects.
    """

    @abstractmethod
    def load(self, source: Path | str) -> list[T]:
        """Load domain objects from a data source.

        Args:
            source: Path to data file or data source identifier

        Returns:
            List of loaded domain objects

        Raises:
            DataLoadingError: If loading fails
        """
        pass
