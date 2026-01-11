"""Registry for data ingesters.

This module provides a registry for auto-discovering and managing available ingesters.
Uses the same Registry pattern as Shape Shifter's Dispatchers.
"""

from typing import Type

from backend.app.ingesters.protocol import Ingester, IngesterMetadata
from src.utility import Registry


class IngesterRegistry(Registry[Type[Ingester]]):
    """Registry for data ingesters.
    
    Ingesters register themselves using the @Ingesters.register() decorator.
    
    Example:
        @Ingesters.register(key="sead")
        class SeadIngester:
            @classmethod
            def get_metadata(cls) -> IngesterMetadata:
                return IngesterMetadata(
                    key="sead",
                    name="SEAD Clearinghouse",
                    description="Ingest data into SEAD database",
                    version="1.0.0",
                    supported_formats=["xlsx"],
                    requires_config=True,
                )
            
            async def validate(self, excel_file: Path | str) -> ValidationResult:
                ...
            
            async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
                ...
    """

    items: dict[str, Type[Ingester]] = {}

    def get_metadata_list(self) -> list[IngesterMetadata]:
        """Get metadata for all registered ingesters.
        
        Returns:
            List of IngesterMetadata for all registered ingesters
        """
        return [cls.get_metadata() for cls in self.items.values()]


# Global registry instance
Ingesters = IngesterRegistry()
