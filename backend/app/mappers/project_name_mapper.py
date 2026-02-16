"""Project name ↔ filesystem path mapping.

Handles conversion between API-safe project names and filesystem paths.
Centralizes the separator logic to ensure consistency across the application.
"""


class ProjectNameMapper:
    """Maps between API project names and filesystem paths.

    Architecture:
        API Layer (URL-safe):    Uses ':' separator → 'arbodat:arbodat-copy'
        Filesystem (standard):   Uses '/' separator → 'arbodat/arbodat-copy'

    Benefits:
        - Avoids URL path parsing issues (FastAPI route parameters)
        - Single conversion point for maintenance
        - Explicit and self-documenting
        - Easy to change separator strategy later
    """

    SEPARATOR_API = ":"
    SEPARATOR_PATH = "/"

    @classmethod
    def to_path(cls, api_name: str) -> str:
        """Convert API project name to filesystem path.

        Args:
            api_name: Project name from API (e.g., 'arbodat:arbodat-copy')

        Returns:
            Filesystem path (e.g., 'arbodat/arbodat-copy')

        Examples:
            >>> ProjectNameMapper.to_path('aDNA-pilot')
            'aDNA-pilot'
            >>> ProjectNameMapper.to_path('arbodat:arbodat-copy')
            'arbodat/arbodat-copy'
        """
        return api_name.replace(cls.SEPARATOR_API, cls.SEPARATOR_PATH)

    @classmethod
    def to_api_name(cls, path: str) -> str:
        """Convert filesystem path to API project name.

        Args:
            path: Filesystem path (e.g., 'arbodat/arbodat-copy')

        Returns:
            API project name (e.g., 'arbodat:arbodat-copy')

        Examples:
            >>> ProjectNameMapper.to_api_name('aDNA-pilot')
            'aDNA-pilot'
            >>> ProjectNameMapper.to_api_name('arbodat/arbodat-copy')
            'arbodat:arbodat-copy'
        """
        return path.replace(cls.SEPARATOR_PATH, cls.SEPARATOR_API)
