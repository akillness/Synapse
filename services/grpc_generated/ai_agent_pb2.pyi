from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class AgentRequest(_message.Message):
    __slots__ = ("request_id", "source_agent", "target_agent", "method", "payload", "metadata", "timestamp")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_AGENT_FIELD_NUMBER: _ClassVar[int]
    TARGET_AGENT_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    source_agent: str
    target_agent: str
    method: str
    payload: bytes
    metadata: _containers.ScalarMap[str, str]
    timestamp: int
    def __init__(self, request_id: str | None = ..., source_agent: str | None = ..., target_agent: str | None = ..., method: str | None = ..., payload: bytes | None = ..., metadata: _Mapping[str, str] | None = ..., timestamp: int | None = ...) -> None: ...

class AgentResponse(_message.Message):
    __slots__ = ("request_id", "success", "result", "error_message", "error_code", "timestamp")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    success: bool
    result: bytes
    error_message: str
    error_code: int
    timestamp: int
    def __init__(self, request_id: str | None = ..., success: bool = ..., result: bytes | None = ..., error_message: str | None = ..., error_code: int | None = ..., timestamp: int | None = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ("service",)
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    service: str
    def __init__(self, service: str | None = ...) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status", "version", "uptime_seconds", "active_connections")
    class ServingStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[HealthCheckResponse.ServingStatus]
        SERVING: _ClassVar[HealthCheckResponse.ServingStatus]
        NOT_SERVING: _ClassVar[HealthCheckResponse.ServingStatus]
        SERVICE_UNKNOWN: _ClassVar[HealthCheckResponse.ServingStatus]
    UNKNOWN: HealthCheckResponse.ServingStatus
    SERVING: HealthCheckResponse.ServingStatus
    NOT_SERVING: HealthCheckResponse.ServingStatus
    SERVICE_UNKNOWN: HealthCheckResponse.ServingStatus
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_CONNECTIONS_FIELD_NUMBER: _ClassVar[int]
    status: HealthCheckResponse.ServingStatus
    version: str
    uptime_seconds: int
    active_connections: int
    def __init__(self, status: HealthCheckResponse.ServingStatus | str | None = ..., version: str | None = ..., uptime_seconds: int | None = ..., active_connections: int | None = ...) -> None: ...

class PlanRequest(_message.Message):
    __slots__ = ("task_description", "context_files", "constraints", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    TASK_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FILES_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    task_description: str
    context_files: _containers.RepeatedScalarFieldContainer[str]
    constraints: _containers.RepeatedScalarFieldContainer[str]
    options: _containers.ScalarMap[str, str]
    def __init__(self, task_description: str | None = ..., context_files: _Iterable[str] | None = ..., constraints: _Iterable[str] | None = ..., options: _Mapping[str, str] | None = ...) -> None: ...

class PlanResponse(_message.Message):
    __slots__ = ("task", "steps", "total_steps", "estimated_agents", "created_at")
    class PlanStep(_message.Message):
        __slots__ = ("order", "phase", "action", "agent", "description", "params")
        class ParamsEntry(_message.Message):
            __slots__ = ("key", "value")
            KEY_FIELD_NUMBER: _ClassVar[int]
            VALUE_FIELD_NUMBER: _ClassVar[int]
            key: str
            value: str
            def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
        ORDER_FIELD_NUMBER: _ClassVar[int]
        PHASE_FIELD_NUMBER: _ClassVar[int]
        ACTION_FIELD_NUMBER: _ClassVar[int]
        AGENT_FIELD_NUMBER: _ClassVar[int]
        DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
        PARAMS_FIELD_NUMBER: _ClassVar[int]
        order: int
        phase: str
        action: str
        agent: str
        description: str
        params: _containers.ScalarMap[str, str]
        def __init__(self, order: int | None = ..., phase: str | None = ..., action: str | None = ..., agent: str | None = ..., description: str | None = ..., params: _Mapping[str, str] | None = ...) -> None: ...
    TASK_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_STEPS_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_AGENTS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    task: str
    steps: _containers.RepeatedCompositeFieldContainer[PlanResponse.PlanStep]
    total_steps: int
    estimated_agents: _containers.RepeatedScalarFieldContainer[str]
    created_at: str
    def __init__(self, task: str | None = ..., steps: _Iterable[PlanResponse.PlanStep | _Mapping] | None = ..., total_steps: int | None = ..., estimated_agents: _Iterable[str] | None = ..., created_at: str | None = ...) -> None: ...

class GenerateCodeRequest(_message.Message):
    __slots__ = ("description", "language", "context", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    description: str
    language: str
    context: str
    options: _containers.ScalarMap[str, str]
    def __init__(self, description: str | None = ..., language: str | None = ..., context: str | None = ..., options: _Mapping[str, str] | None = ...) -> None: ...

class GenerateCodeResponse(_message.Message):
    __slots__ = ("language", "code", "description", "generated_at")
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    GENERATED_AT_FIELD_NUMBER: _ClassVar[int]
    language: str
    code: str
    description: str
    generated_at: str
    def __init__(self, language: str | None = ..., code: str | None = ..., description: str | None = ..., generated_at: str | None = ...) -> None: ...

class OrchestrateRequest(_message.Message):
    __slots__ = ("workflow_id", "workflow", "context")
    class ContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    class WorkflowStep(_message.Message):
        __slots__ = ("order", "agent", "action", "params")
        ORDER_FIELD_NUMBER: _ClassVar[int]
        AGENT_FIELD_NUMBER: _ClassVar[int]
        ACTION_FIELD_NUMBER: _ClassVar[int]
        PARAMS_FIELD_NUMBER: _ClassVar[int]
        order: int
        agent: str
        action: str
        params: bytes
        def __init__(self, order: int | None = ..., agent: str | None = ..., action: str | None = ..., params: bytes | None = ...) -> None: ...
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    workflow_id: str
    workflow: _containers.RepeatedCompositeFieldContainer[OrchestrateRequest.WorkflowStep]
    context: _containers.ScalarMap[str, str]
    def __init__(self, workflow_id: str | None = ..., workflow: _Iterable[OrchestrateRequest.WorkflowStep | _Mapping] | None = ..., context: _Mapping[str, str] | None = ...) -> None: ...

class OrchestrateResponse(_message.Message):
    __slots__ = ("workflow_id", "results", "completed", "completed_at")
    class StepResult(_message.Message):
        __slots__ = ("step", "agent", "action", "status", "result", "completed_at")
        STEP_FIELD_NUMBER: _ClassVar[int]
        AGENT_FIELD_NUMBER: _ClassVar[int]
        ACTION_FIELD_NUMBER: _ClassVar[int]
        STATUS_FIELD_NUMBER: _ClassVar[int]
        RESULT_FIELD_NUMBER: _ClassVar[int]
        COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
        step: int
        agent: str
        action: str
        status: str
        result: bytes
        completed_at: str
        def __init__(self, step: int | None = ..., agent: str | None = ..., action: str | None = ..., status: str | None = ..., result: bytes | None = ..., completed_at: str | None = ...) -> None: ...
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    workflow_id: str
    results: _containers.RepeatedCompositeFieldContainer[OrchestrateResponse.StepResult]
    completed: bool
    completed_at: str
    def __init__(self, workflow_id: str | None = ..., results: _Iterable[OrchestrateResponse.StepResult | _Mapping] | None = ..., completed: bool = ..., completed_at: str | None = ...) -> None: ...

class AnalyzeRequest(_message.Message):
    __slots__ = ("content", "analysis_type", "max_tokens", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ANALYSIS_TYPE_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    content: str
    analysis_type: str
    max_tokens: int
    options: _containers.ScalarMap[str, str]
    def __init__(self, content: str | None = ..., analysis_type: str | None = ..., max_tokens: int | None = ..., options: _Mapping[str, str] | None = ...) -> None: ...

class AnalyzeResponse(_message.Message):
    __slots__ = ("analysis_type", "content_length", "token_estimate", "findings", "summary", "analyzed_at")
    class Finding(_message.Message):
        __slots__ = ("category", "severity", "description", "suggestion")
        CATEGORY_FIELD_NUMBER: _ClassVar[int]
        SEVERITY_FIELD_NUMBER: _ClassVar[int]
        DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
        SUGGESTION_FIELD_NUMBER: _ClassVar[int]
        category: str
        severity: str
        description: str
        suggestion: str
        def __init__(self, category: str | None = ..., severity: str | None = ..., description: str | None = ..., suggestion: str | None = ...) -> None: ...
    ANALYSIS_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_LENGTH_FIELD_NUMBER: _ClassVar[int]
    TOKEN_ESTIMATE_FIELD_NUMBER: _ClassVar[int]
    FINDINGS_FIELD_NUMBER: _ClassVar[int]
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    ANALYZED_AT_FIELD_NUMBER: _ClassVar[int]
    analysis_type: str
    content_length: int
    token_estimate: int
    findings: _containers.RepeatedCompositeFieldContainer[AnalyzeResponse.Finding]
    summary: str
    analyzed_at: str
    def __init__(self, analysis_type: str | None = ..., content_length: int | None = ..., token_estimate: int | None = ..., findings: _Iterable[AnalyzeResponse.Finding | _Mapping] | None = ..., summary: str | None = ..., analyzed_at: str | None = ...) -> None: ...

class ReviewCodeRequest(_message.Message):
    __slots__ = ("code", "language", "review_type", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    REVIEW_TYPE_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    code: str
    language: str
    review_type: str
    options: _containers.ScalarMap[str, str]
    def __init__(self, code: str | None = ..., language: str | None = ..., review_type: str | None = ..., options: _Mapping[str, str] | None = ...) -> None: ...

class ReviewCodeResponse(_message.Message):
    __slots__ = ("language", "review_type", "code_length", "issues", "overall_score", "reviewed_at")
    class Issue(_message.Message):
        __slots__ = ("type", "severity", "line", "message", "suggestion")
        TYPE_FIELD_NUMBER: _ClassVar[int]
        SEVERITY_FIELD_NUMBER: _ClassVar[int]
        LINE_FIELD_NUMBER: _ClassVar[int]
        MESSAGE_FIELD_NUMBER: _ClassVar[int]
        SUGGESTION_FIELD_NUMBER: _ClassVar[int]
        type: str
        severity: str
        line: int
        message: str
        suggestion: str
        def __init__(self, type: str | None = ..., severity: str | None = ..., line: int | None = ..., message: str | None = ..., suggestion: str | None = ...) -> None: ...
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    REVIEW_TYPE_FIELD_NUMBER: _ClassVar[int]
    CODE_LENGTH_FIELD_NUMBER: _ClassVar[int]
    ISSUES_FIELD_NUMBER: _ClassVar[int]
    OVERALL_SCORE_FIELD_NUMBER: _ClassVar[int]
    REVIEWED_AT_FIELD_NUMBER: _ClassVar[int]
    language: str
    review_type: str
    code_length: int
    issues: _containers.RepeatedCompositeFieldContainer[ReviewCodeResponse.Issue]
    overall_score: float
    reviewed_at: str
    def __init__(self, language: str | None = ..., review_type: str | None = ..., code_length: int | None = ..., issues: _Iterable[ReviewCodeResponse.Issue | _Mapping] | None = ..., overall_score: float | None = ..., reviewed_at: str | None = ...) -> None: ...

class ResearchRequest(_message.Message):
    __slots__ = ("query", "sources", "depth")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    query: str
    sources: _containers.RepeatedScalarFieldContainer[str]
    depth: str
    def __init__(self, query: str | None = ..., sources: _Iterable[str] | None = ..., depth: str | None = ...) -> None: ...

class ResearchResponse(_message.Message):
    __slots__ = ("query", "depth", "results", "sources_consulted", "researched_at")
    class ResearchResult(_message.Message):
        __slots__ = ("topic", "finding", "confidence", "relevance")
        TOPIC_FIELD_NUMBER: _ClassVar[int]
        FINDING_FIELD_NUMBER: _ClassVar[int]
        CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
        RELEVANCE_FIELD_NUMBER: _ClassVar[int]
        topic: str
        finding: str
        confidence: float
        relevance: str
        def __init__(self, topic: str | None = ..., finding: str | None = ..., confidence: float | None = ..., relevance: str | None = ...) -> None: ...
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_CONSULTED_FIELD_NUMBER: _ClassVar[int]
    RESEARCHED_AT_FIELD_NUMBER: _ClassVar[int]
    query: str
    depth: str
    results: _containers.RepeatedCompositeFieldContainer[ResearchResponse.ResearchResult]
    sources_consulted: int
    researched_at: str
    def __init__(self, query: str | None = ..., depth: str | None = ..., results: _Iterable[ResearchResponse.ResearchResult | _Mapping] | None = ..., sources_consulted: int | None = ..., researched_at: str | None = ...) -> None: ...

class ExecuteRequest(_message.Message):
    __slots__ = ("command", "working_dir", "environment", "timeout_seconds")
    class EnvironmentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIR_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    command: str
    working_dir: str
    environment: _containers.ScalarMap[str, str]
    timeout_seconds: int
    def __init__(self, command: str | None = ..., working_dir: str | None = ..., environment: _Mapping[str, str] | None = ..., timeout_seconds: int | None = ...) -> None: ...

class ExecuteResponse(_message.Message):
    __slots__ = ("success", "command", "exit_code", "stdout", "stderr", "duration_seconds", "executed_at")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    STDOUT_FIELD_NUMBER: _ClassVar[int]
    STDERR_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    EXECUTED_AT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    executed_at: str
    def __init__(self, success: bool = ..., command: str | None = ..., exit_code: int | None = ..., stdout: str | None = ..., stderr: str | None = ..., duration_seconds: float | None = ..., executed_at: str | None = ...) -> None: ...

class BuildRequest(_message.Message):
    __slots__ = ("project_dir", "build_command", "environment")
    class EnvironmentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    BUILD_COMMAND_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    project_dir: str
    build_command: str
    environment: _containers.ScalarMap[str, str]
    def __init__(self, project_dir: str | None = ..., build_command: str | None = ..., environment: _Mapping[str, str] | None = ...) -> None: ...

class BuildResponse(_message.Message):
    __slots__ = ("success", "project_dir", "build_command", "exit_code", "stdout", "stderr", "duration_seconds", "built_at")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    BUILD_COMMAND_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    STDOUT_FIELD_NUMBER: _ClassVar[int]
    STDERR_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    BUILT_AT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    project_dir: str
    build_command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    built_at: str
    def __init__(self, success: bool = ..., project_dir: str | None = ..., build_command: str | None = ..., exit_code: int | None = ..., stdout: str | None = ..., stderr: str | None = ..., duration_seconds: float | None = ..., built_at: str | None = ...) -> None: ...

class TestRequest(_message.Message):
    __slots__ = ("project_dir", "test_command", "coverage")
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    TEST_COMMAND_FIELD_NUMBER: _ClassVar[int]
    COVERAGE_FIELD_NUMBER: _ClassVar[int]
    project_dir: str
    test_command: str
    coverage: bool
    def __init__(self, project_dir: str | None = ..., test_command: str | None = ..., coverage: bool = ...) -> None: ...

class TestResponse(_message.Message):
    __slots__ = ("success", "project_dir", "test_command", "exit_code", "output", "errors", "test_results", "duration_seconds", "tested_at")
    class TestResults(_message.Message):
        __slots__ = ("passed", "failed", "skipped", "coverage_percent")
        PASSED_FIELD_NUMBER: _ClassVar[int]
        FAILED_FIELD_NUMBER: _ClassVar[int]
        SKIPPED_FIELD_NUMBER: _ClassVar[int]
        COVERAGE_PERCENT_FIELD_NUMBER: _ClassVar[int]
        passed: int
        failed: int
        skipped: int
        coverage_percent: float
        def __init__(self, passed: int | None = ..., failed: int | None = ..., skipped: int | None = ..., coverage_percent: float | None = ...) -> None: ...
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    TEST_COMMAND_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    TEST_RESULTS_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    TESTED_AT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    project_dir: str
    test_command: str
    exit_code: int
    output: str
    errors: str
    test_results: TestResponse.TestResults
    duration_seconds: float
    tested_at: str
    def __init__(self, success: bool = ..., project_dir: str | None = ..., test_command: str | None = ..., exit_code: int | None = ..., output: str | None = ..., errors: str | None = ..., test_results: TestResponse.TestResults | _Mapping | None = ..., duration_seconds: float | None = ..., tested_at: str | None = ...) -> None: ...

class DeployRequest(_message.Message):
    __slots__ = ("target", "config", "dry_run")
    class ConfigEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...
    TARGET_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    target: str
    config: _containers.ScalarMap[str, str]
    dry_run: bool
    def __init__(self, target: str | None = ..., config: _Mapping[str, str] | None = ..., dry_run: bool = ...) -> None: ...

class DeployResponse(_message.Message):
    __slots__ = ("success", "target", "dry_run", "message", "steps", "deployed_at")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    DEPLOYED_AT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    target: str
    dry_run: bool
    message: str
    steps: _containers.RepeatedScalarFieldContainer[str]
    deployed_at: str
    def __init__(self, success: bool = ..., target: str | None = ..., dry_run: bool = ..., message: str | None = ..., steps: _Iterable[str] | None = ..., deployed_at: str | None = ...) -> None: ...

class StreamMessage(_message.Message):
    __slots__ = ("stream_id", "type", "content", "progress_percent", "timestamp")
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_PERCENT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    stream_id: str
    type: str
    content: str
    progress_percent: float
    timestamp: int
    def __init__(self, stream_id: str | None = ..., type: str | None = ..., content: str | None = ..., progress_percent: float | None = ..., timestamp: int | None = ...) -> None: ...
