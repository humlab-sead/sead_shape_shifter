"""Register project-load issue collectors."""

from backend.app.mappers.fixed_entity_load_issue_collector import FixedEntityLoadIssueCollector
from backend.app.mappers.project_load_issue_collector import ProjectLoadIssueCollectorRegistry

PROJECT_LOAD_ISSUE_COLLECTORS = ProjectLoadIssueCollectorRegistry()
PROJECT_LOAD_ISSUE_COLLECTORS.register("fixed_entity", FixedEntityLoadIssueCollector())
