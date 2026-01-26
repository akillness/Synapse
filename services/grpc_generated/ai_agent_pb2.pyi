from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AgentRequest(_message.Message):
    __slots__ = ("request_id", "source_agent", "target_agent", "method", "payload", "metadata", "timestamp")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
    def __init__(self, request_id: _Optional[str] = ..., source_agent: _Optional[str] = ..., target_agent: _Optional[str] = ..., method: _Optional[str] = ..., payload: _Optional[bytes] = ..., metadata: _Optional[_Mapping[str, str]] = ..., timestamp: _Optional[int] = ...) -> None: ...

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
    def __init__(self, request_id: _Optional[str] = ..., success: bool = ..., result: _Optional[bytes] = ..., error_message: _Optional[str] = ..., error_code: _Optional[int] = ..., timestamp: _Optional[int] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ("service",)
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    service: str
    def __init__(self, service: _Optional[str] = ...) -> None: ...

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
    def __init__(self, status: _Optional[_Union[HealthCheckResponse.ServingStatus, str]] = ..., version: _Optional[str] = ..., uptime_seconds: _Optional[int] = ..., active_connections: _Optional[int] = ...) -> None: ...

class PlanRequest(_message.Message):
    __slots__ = ("task_description", "context_files", "constraints", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TASK_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FILES_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    task_description: str
    context_files: _containers.RepeatedScalarFieldContainer[str]
    constraints: _containers.RepeatedScalarFieldContainer[str]
    options: _containers.ScalarMap[str, str]
    def __init__(self, task_description: _Optional[str] = ..., context_files: _Optional[_Iterable[str]] = ..., constraints: _Optional[_Iterable[str]] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
            def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
        def __init__(self, order: _Optional[int] = ..., phase: _Optional[str] = ..., action: _Optional[str] = ..., agent: _Optional[str] = ..., description: _Optional[str] = ..., params: _Optional[_Mapping[str, str]] = ...) -> None: ...
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
    def __init__(self, task: _Optional[str] = ..., steps: _Optional[_Iterable[_Union[PlanResponse.PlanStep, _Mapping]]] = ..., total_steps: _Optional[int] = ..., estimated_agents: _Optional[_Iterable[str]] = ..., created_at: _Optional[str] = ...) -> None: ...

class GenerateCodeRequest(_message.Message):
    __slots__ = ("description", "language", "context", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    description: str
    language: str
    context: str
    options: _containers.ScalarMap[str, str]
    def __init__(self, description: _Optional[str] = ..., language: _Optional[str] = ..., context: _Optional[str] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
    def __init__(self, language: _Optional[str] = ..., code: _Optional[str] = ..., description: _Optional[str] = ..., generated_at: _Optional[str] = ...) -> None: ...

class OrchestrateRequest(_message.Message):
    __slots__ = ("workflow_id", "workflow", "context")
    class ContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
        def __init__(self, order: _Optional[int] = ..., agent: _Optional[str] = ..., action: _Optional[str] = ..., params: _Optional[bytes] = ...) -> None: ...
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    workflow_id: str
    workflow: _containers.RepeatedCompositeFieldContainer[OrchestrateRequest.WorkflowStep]
    context: _containers.ScalarMap[str, str]
    def __init__(self, workflow_id: _Optional[str] = ..., workflow: _Optional[_Iterable[_Union[OrchestrateRequest.WorkflowStep, _Mapping]]] = ..., context: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
        def __init__(self, step: _Optional[int] = ..., agent: _Optional[str] = ..., action: _Optional[str] = ..., status: _Optional[str] = ..., result: _Optional[bytes] = ..., completed_at: _Optional[str] = ...) -> None: ...
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    workflow_id: str
    results: _containers.RepeatedCompositeFieldContainer[OrchestrateResponse.StepResult]
    completed: bool
    completed_at: str
    def __init__(self, workflow_id: _Optional[str] = ..., results: _Optional[_Iterable[_Union[OrchestrateResponse.StepResult, _Mapping]]] = ..., completed: bool = ..., completed_at: _Optional[str] = ...) -> None: ...

class AnalyzeRequest(_message.Message):
    __slots__ = ("content", "analysis_type", "max_tokens", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ANALYSIS_TYPE_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    content: str
    analysis_type: str
    max_tokens: int
    options: _containers.ScalarMap[str, str]
    def __init__(self, content: _Optional[str] = ..., analysis_type: _Optional[str] = ..., max_tokens: _Optional[int] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
        def __init__(self, category: _Optional[str] = ..., severity: _Optional[str] = ..., description: _Optional[str] = ..., suggestion: _Optional[str] = ...) -> None: ...
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
    def __init__(self, analysis_type: _Optional[str] = ..., content_length: _Optional[int] = ..., token_estimate: _Optional[int] = ..., findings: _Optional[_Iterable[_Union[AnalyzeResponse.Finding, _Mapping]]] = ..., summary: _Optional[str] = ..., analyzed_at: _Optional[str] = ...) -> None: ...

class ReviewCodeRequest(_message.Message):
    __slots__ = ("code", "language", "review_type", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    REVIEW_TYPE_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    code: str
    language: str
    review_type: str
    options: _containers.ScalarMap[str, str]
    def __init__(self, code: _Optional[str] = ..., language: _Optional[str] = ..., review_type: _Optional[str] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
        def __init__(self, type: _Optional[str] = ..., severity: _Optional[str] = ..., line: _Optional[int] = ..., message: _Optional[str] = ..., suggestion: _Optional[str] = ...) -> None: ...
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
    def __init__(self, language: _Optional[str] = ..., review_type: _Optional[str] = ..., code_length: _Optional[int] = ..., issues: _Optional[_Iterable[_Union[ReviewCodeResponse.Issue, _Mapping]]] = ..., overall_score: _Optional[float] = ..., reviewed_at: _Optional[str] = ...) -> None: ...

class ResearchRequest(_message.Message):
    __slots__ = ("query", "sources", "depth")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    query: str
    sources: _containers.RepeatedScalarFieldContainer[str]
    depth: str
    def __init__(self, query: _Optional[str] = ..., sources: _Optional[_Iterable[str]] = ..., depth: _Optional[str] = ...) -> None: ...

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
        def __init__(self, topic: _Optional[str] = ..., finding: _Optional[str] = ..., confidence: _Optional[float] = ..., relevance: _Optional[str] = ...) -> None: ...
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
    def __init__(self, query: _Optional[str] = ..., depth: _Optional[str] = ..., results: _Optional[_Iterable[_Union[ResearchResponse.ResearchResult, _Mapping]]] = ..., sources_consulted: _Optional[int] = ..., researched_at: _Optional[str] = ...) -> None: ...

class ExecuteRequest(_message.Message):
    __slots__ = ("command", "working_dir", "environment", "timeout_seconds")
    class EnvironmentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIR_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    command: str
    working_dir: str
    environment: _containers.ScalarMap[str, str]
    timeout_seconds: int
    def __init__(self, command: _Optional[str] = ..., working_dir: _Optional[str] = ..., environment: _Optional[_Mapping[str, str]] = ..., timeout_seconds: _Optional[int] = ...) -> None: ...

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
    def __init__(self, success: bool = ..., command: _Optional[str] = ..., exit_code: _Optional[int] = ..., stdout: _Optional[str] = ..., stderr: _Optional[str] = ..., duration_seconds: _Optional[float] = ..., executed_at: _Optional[str] = ...) -> None: ...

class BuildRequest(_message.Message):
    __slots__ = ("project_dir", "build_command", "environment")
    class EnvironmentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    BUILD_COMMAND_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    project_dir: str
    build_command: str
    environment: _containers.ScalarMap[str, str]
    def __init__(self, project_dir: _Optional[str] = ..., build_command: _Optional[str] = ..., environment: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
    def __init__(self, success: bool = ..., project_dir: _Optional[str] = ..., build_command: _Optional[str] = ..., exit_code: _Optional[int] = ..., stdout: _Optional[str] = ..., stderr: _Optional[str] = ..., duration_seconds: _Optional[float] = ..., built_at: _Optional[str] = ...) -> None: ...

class TestRequest(_message.Message):
    __slots__ = ("project_dir", "test_command", "coverage")
    PROJECT_DIR_FIELD_NUMBER: _ClassVar[int]
    TEST_COMMAND_FIELD_NUMBER: _ClassVar[int]
    COVERAGE_FIELD_NUMBER: _ClassVar[int]
    project_dir: str
    test_command: str
    coverage: bool
    def __init__(self, project_dir: _Optional[str] = ..., test_command: _Optional[str] = ..., coverage: bool = ...) -> None: ...

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
        def __init__(self, passed: _Optional[int] = ..., failed: _Optional[int] = ..., skipped: _Optional[int] = ..., coverage_percent: _Optional[float] = ...) -> None: ...
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
    def __init__(self, success: bool = ..., project_dir: _Optional[str] = ..., test_command: _Optional[str] = ..., exit_code: _Optional[int] = ..., output: _Optional[str] = ..., errors: _Optional[str] = ..., test_results: _Optional[_Union[TestResponse.TestResults, _Mapping]] = ..., duration_seconds: _Optional[float] = ..., tested_at: _Optional[str] = ...) -> None: ...

class DeployRequest(_message.Message):
    __slots__ = ("target", "config", "dry_run")
    class ConfigEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TARGET_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    target: str
    config: _containers.ScalarMap[str, str]
    dry_run: bool
    def __init__(self, target: _Optional[str] = ..., config: _Optional[_Mapping[str, str]] = ..., dry_run: bool = ...) -> None: ...

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
    def __init__(self, success: bool = ..., target: _Optional[str] = ..., dry_run: bool = ..., message: _Optional[str] = ..., steps: _Optional[_Iterable[str]] = ..., deployed_at: _Optional[str] = ...) -> None: ...

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
    def __init__(self, stream_id: _Optional[str] = ..., type: _Optional[str] = ..., content: _Optional[str] = ..., progress_percent: _Optional[float] = ..., timestamp: _Optional[int] = ...) -> None: ...
