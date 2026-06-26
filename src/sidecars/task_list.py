from typing import Any


class TaskList:
    """Task list configuration for tracking entity progress.

    This class provides a lightweight, non-enforcing progress tracking system
    for entities in a Shape Shifter project. It combines user-declared statuses
    with derived state (validation, preview availability) to guide workflow.

    Status Model:
        - todo: Entity planned but not yet created (yellowish color)
        - ongoing: Entity exists and is being worked on (bluish color)
        - done: User explicitly marked as complete (greenish color)
        - ignored: User explicitly excluded from project (greyish color)

    Derived Signals:
        - blocked: Has validation errors or dependency issues
        - flagged: User flagged for attention or action needed
        - critical: Required entity missing or has errors
        - ready: All dependencies done, validation passes
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize task list from configuration data.

        Args:
            data: Dictionary containing task list configuration with keys:
                - todo: List of entity names that are planned but not yet created
                - ongoing: List of entity names marked as in-progress by user
                - done: List of entity names marked as complete by user
                - ignored: List of entity names explicitly excluded
                - flagged: Dictionary mapping entity names to flagged status

        Note:
            Automatically migrates old format (required_entities/completed) to new format (todo/done).
        """
        self.data: dict[str, Any] = data or {}
        self._migrate_legacy_format()

    def _migrate_legacy_format(self) -> None:
        """Migrate old format (required_entities/completed) to new format (todo/done).

        Old format:
            required_entities: [location, site, sample]
            completed: [location, site]

        New format:
            todo: [sample]
            done: [location, site]

        Migration logic:
            - done = completed
            - todo = required_entities - completed - ongoing
            - Remove old keys after migration
        """
        if "required_entities" in self.data or "completed" in self.data:
            # Get old values
            required = set(self.data.get("required_entities", []) or [])
            completed_old = set(self.data.get("completed", []) or [])
            ongoing_existing = set(self.data.get("ongoing", []) or [])

            # Migrate to new format
            if completed_old:
                self.data.setdefault("done", []).extend(sorted(completed_old))

            # Calculate todo: entities in required but not completed and not ongoing
            todo_entities = required - completed_old - ongoing_existing
            if todo_entities:
                self.data.setdefault("todo", []).extend(sorted(todo_entities))

            # Remove old keys
            self.data.pop("required_entities", None)
            self.data.pop("completed", None)

    @property
    def todo(self) -> list[str]:
        """Get list of todo entity names (planned but not yet created)."""
        return self.data.get("todo", []) or []

    @property
    def done(self) -> list[str]:
        """Get list of completed entity names."""
        return self.data.get("done", []) or []

    @property
    def required_entities(self) -> list[str]:
        """Get list of required entity names (for backward compatibility).

        Returns union of todo and done entities.
        """
        return sorted(set(self.todo) | set(self.done))

    @property
    def completed(self) -> list[str]:
        """Get list of completed entity names (for backward compatibility).

        Alias for done property.
        """
        return self.done

    @property
    def ongoing(self) -> list[str]:
        """Get list of ongoing entity names."""
        return self.data.get("ongoing", []) or []

    @property
    def ignored(self) -> list[str]:
        """Get list of ignored entity names."""
        return self.data.get("ignored", []) or []

    @property
    def flagged(self) -> dict[str, bool]:
        """Get mapping of flagged entity statuses."""
        return self.data.get("flagged", {}) or {}

    def is_required(self, entity_name: str) -> bool:
        """Check if entity is required (in todo or done lists)."""
        return entity_name in self.todo or entity_name in self.done

    def is_todo(self, entity_name: str) -> bool:
        """Check if entity is marked as todo."""
        return entity_name in self.todo

    def is_completed(self, entity_name: str) -> bool:
        """Check if entity is marked as completed."""
        return entity_name in self.done

    def is_done(self, entity_name: str) -> bool:
        """Check if entity is marked as done (alias for is_completed)."""
        return entity_name in self.done

    def is_ongoing(self, entity_name: str) -> bool:
        """Check if entity is marked as ongoing."""
        return entity_name in self.ongoing

    def is_ignored(self, entity_name: str) -> bool:
        """Check if entity is marked as ignored."""
        return entity_name in self.ignored

    def is_flagged(self, entity_name: str) -> bool:
        """Check if entity is flagged."""
        return self.flagged.get(entity_name, False)

    def mark_completed(self, entity_name: str) -> None:
        """Mark entity as completed.

        Args:
            entity_name: Name of entity to mark as done

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure done list exists in data
        if "done" not in self.data:
            self.data["done"] = []

        # Add to done list if not already there
        if entity_name not in self.data["done"]:
            self.data["done"].append(entity_name)

        # Remove from todo, ongoing, and ignored if present
        if "todo" in self.data and entity_name in self.data["todo"]:
            self.data["todo"] = [e for e in self.data["todo"] if e != entity_name]
        if "ongoing" in self.data and entity_name in self.data["ongoing"]:
            self.data["ongoing"] = [e for e in self.data["ongoing"] if e != entity_name]
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def mark_ongoing(self, entity_name: str) -> None:
        """Mark entity as ongoing.

        Args:
            entity_name: Name of entity to mark as ongoing

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure ongoing list exists in data
        if "ongoing" not in self.data:
            self.data["ongoing"] = []

        # Add to ongoing list if not already there
        if entity_name not in self.data["ongoing"]:
            self.data["ongoing"].append(entity_name)

        # Remove from todo, done, and ignored if present
        if "todo" in self.data and entity_name in self.data["todo"]:
            self.data["todo"] = [e for e in self.data["todo"] if e != entity_name]
        if "done" in self.data and entity_name in self.data["done"]:
            self.data["done"] = [e for e in self.data["done"] if e != entity_name]
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def mark_ignored(self, entity_name: str) -> None:
        """Mark entity as ignored.

        Args:
            entity_name: Name of entity to ignore

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure ignored list exists in data
        if "ignored" not in self.data:
            self.data["ignored"] = []

        # Add to ignored list if not already there
        if entity_name not in self.data["ignored"]:
            self.data["ignored"].append(entity_name)

        # Remove from todo, done, and ongoing if present
        if "todo" in self.data and entity_name in self.data["todo"]:
            self.data["todo"] = [e for e in self.data["todo"] if e != entity_name]
        if "done" in self.data and entity_name in self.data["done"]:
            self.data["done"] = [e for e in self.data["done"] if e != entity_name]
        if "ongoing" in self.data and entity_name in self.data["ongoing"]:
            self.data["ongoing"] = [e for e in self.data["ongoing"] if e != entity_name]

    def toggle_flagged(self, entity_name: str) -> bool:
        """Toggle flagged status for an entity.

        Args:
            entity_name: Name of entity to toggle

        Returns:
            New flagged status after toggle

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        if "flagged" not in self.data:
            self.data["flagged"] = {}

        current = self.data["flagged"].get(entity_name, False)
        new_status = not current
        self.data["flagged"][entity_name] = new_status
        return new_status

    def mark_todo(self, entity_name: str) -> None:
        """Mark entity as todo (planned but not yet created).

        Args:
            entity_name: Name of entity to mark as todo

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure todo list exists in data
        if "todo" not in self.data:
            self.data["todo"] = []

        # Add to todo list if not already there
        if entity_name not in self.data["todo"]:
            self.data["todo"].append(entity_name)

        # Remove from done, ongoing, and ignored if present
        if "done" in self.data and entity_name in self.data["done"]:
            self.data["done"] = [e for e in self.data["done"] if e != entity_name]
        if "ongoing" in self.data and entity_name in self.data["ongoing"]:
            self.data["ongoing"] = [e for e in self.data["ongoing"] if e != entity_name]
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def reset_status(self, entity_name: str) -> None:
        """Reset entity status to todo.

        Args:
            entity_name: Name of entity to reset

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Use mark_todo to add to todo list and remove from others
        self.mark_todo(entity_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization (uses new format)."""
        result = {}
        if self.todo:
            result["todo"] = self.todo
        if self.ongoing:
            result["ongoing"] = self.ongoing
        if self.done:
            result["done"] = self.done
        if self.ignored:
            result["ignored"] = self.ignored
        if self.flagged:
            result["flagged"] = self.flagged
        return result

    @property
    def is_empty(self) -> bool:
        """Check if task list has no configuration."""
        return not (self.todo or self.done or self.ongoing or self.ignored)
