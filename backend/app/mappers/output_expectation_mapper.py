"""Mapper for converting Core output expectation results to API models."""

from backend.app.models.execute import OutputExpectationResult as OutputExpectationResultModel
from src.output_expectations import OutputExpectationEvaluation
from src.output_expectations import OutputExpectationResult as CoreOutputExpectationResult


class OutputExpectationMapper:
    """Convert output expectation results across the Core/API boundary."""

    @staticmethod
    def to_api(result: CoreOutputExpectationResult) -> OutputExpectationResultModel:
        """Convert one Core result to its API model without changing its values."""
        return OutputExpectationResultModel(
            name=result.name,
            entity=result.entity,
            metric=result.metric,
            group_value=result.group_value,
            measured_value=result.measured_value,
            expected_limit=dict(result.expected_limit),
            status=result.status,
            failure_reason=result.failure_reason,
        )

    @staticmethod
    def to_api_results(evaluation: OutputExpectationEvaluation | None) -> list[OutputExpectationResultModel]:
        """Convert an evaluation to API models in evaluation order."""
        if evaluation is None:
            return []
        return [OutputExpectationMapper.to_api(result) for result in evaluation.results]
