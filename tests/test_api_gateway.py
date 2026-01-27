import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestApiGatewayModels:
    def test_plan_request_model(self):
        from gateway.api_gateway import PlanRequest

        request = PlanRequest(task="Test task", constraints=["constraint1"])

        assert request.task == "Test task"
        assert request.constraints == ["constraint1"]

    def test_plan_request_optional_constraints(self):
        from gateway.api_gateway import PlanRequest

        request = PlanRequest(task="Test task")

        assert request.task == "Test task"
        assert request.constraints is None

    def test_code_request_model(self):
        from gateway.api_gateway import CodeRequest

        request = CodeRequest(description="A hello function", language="python")

        assert request.description == "A hello function"
        assert request.language == "python"

    def test_code_request_default_language(self):
        from gateway.api_gateway import CodeRequest

        request = CodeRequest(description="A function")

        assert request.language == "python"

    def test_analyze_request_model(self):
        from gateway.api_gateway import AnalyzeRequest

        request = AnalyzeRequest(content="code content", analysis_type="security")

        assert request.content == "code content"
        assert request.analysis_type == "security"

    def test_review_request_model(self):
        from gateway.api_gateway import ReviewRequest

        request = ReviewRequest(code="def foo(): pass", language="python")

        assert request.code == "def foo(): pass"
        assert request.language == "python"

    def test_execute_request_model(self):
        from gateway.api_gateway import ExecuteRequest

        request = ExecuteRequest(command="ls -la", working_dir="/tmp", timeout=60)

        assert request.command == "ls -la"
        assert request.working_dir == "/tmp"
        assert request.timeout == 60

    def test_execute_request_defaults(self):
        from gateway.api_gateway import ExecuteRequest

        request = ExecuteRequest(command="echo hello")

        assert request.working_dir is None
        assert request.timeout == 30


class TestApiGatewayClientFactories:
    @pytest.mark.asyncio
    async def test_health_check_client_returns_true_on_serving(self):
        from gateway.api_gateway import health_check_client

        mock_client = AsyncMock()
        mock_client.health_check.return_value = {"status": "SERVING"}

        result = await health_check_client(mock_client)

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_client_returns_false_on_non_serving(self):
        from gateway.api_gateway import health_check_client

        mock_client = AsyncMock()
        mock_client.health_check.return_value = {"status": "NOT_SERVING"}

        result = await health_check_client(mock_client)

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_client_returns_false_on_exception(self):
        from gateway.api_gateway import health_check_client

        mock_client = AsyncMock()
        mock_client.health_check.side_effect = Exception("Connection failed")

        result = await health_check_client(mock_client)

        assert result is False


class TestApiGatewayAppCreation:
    def test_app_has_correct_title(self):
        from gateway.api_gateway import create_app

        app = create_app()

        assert app.title == "Synaps AI Agent Gateway"

    def test_app_has_correct_version(self):
        from gateway.api_gateway import create_app

        app = create_app()

        assert app.version == "1.0.0"
