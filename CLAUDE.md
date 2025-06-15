# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Novel Generation Orchestration System that coordinates multiple AI components to generate long-form novels from simple theme inputs. The system employs a "divide and conquer" approach with specialized AI components working together rather than relying on a single LLM.

### Core Architecture

The system orchestrates 4 specialized AI components:

- **Director AI**: Overall process control and result integration
- **Planner AI**: Novel structure planning and task decomposition
- **Worker AI**: Actual novel content generation
- **Reviewer AI**: Quality evaluation and feedback

Components communicate through standardized messaging using `OrchestrationMessage` objects and are managed by a central orchestrator with session-based state management.

## Development Commands

### Testing

```bash
# Run all tests with coverage
uv run pytest

# Run specific component tests
uv run pytest tests/test_director_ai.py
uv run pytest tests/test_planner_ai.py
uv run pytest tests/test_worker_ai.py
uv run pytest tests/test_reviewer_ai.py

# Run comprehensive test suite (includes deterministic output validation)
uv run python tests/run_all_tests.py

# Run slow/integration tests
uv run pytest -m "slow or integration"

# Run with detailed coverage report
uv run pytest --cov=orchestration --cov-report=html
```

### Running the System

```bash
# Run the novel writer CLI
uv run python orchestration/cui/run_novel_writer.py

# Run with custom parameters
uv run python -c "from orchestration.cui.run_novel_writer import run_novel_writer; run_novel_writer(session_id='custom', mode='creative')"

# Run tests with coverage
uv run pytest --cov=orchestration

# Code quality checks
uv run ruff check .
uv run ruff format .
uv run mypy orchestration/
```

### Dependencies Management

```bash
# Install dependencies (uses uv)
uv sync

# Add new dependencies
uv add <package>

# Add development dependencies
uv add --dev <package>

# Update dependencies
uv sync --upgrade

# Run with uv
uv run python <script>
```

## Key Implementation Details

### Component Temperature Settings

- **Planner AI**: `temperature=0.0` for deterministic outputs (ensures consistent planning)
- **Director/Reviewer**: Lower temperature for consistency in control/evaluation
- **Worker**: Variable temperature based on mode (0.8 for creative, 0.3 for coding)

### LLM Integration

- Uses Agno framework (`agno_client.py`) for LLM communication
- Supports Ollama for local LLM hosting (default: `gemma3:27b`)
- Template-based prompt management in `prompts/` directory
- Retry logic with exponential backoff for model loading/timeout issues

### Session Management

- Sessions stored in memory by default (`STORAGE_TYPE="memory"`)
- 24-hour session expiry, max 10 sessions per user
- Session state includes task history, component interactions, and intermediate results

### Message Flow

All component communication follows this pattern:

```python
OrchestrationMessage(
    type=MessageType.COMMAND,  # COMMAND, RESPONSE, ERROR, STATUS, FEEDBACK, QUERY
    sender=component,
    receiver=target_component,
    content={"action": action_name, **params},
    session_id=session.id
)
```

## File Structure Highlights

- `orchestration/components/`: AI component implementations
- `orchestration/llm/llm_manager.py`: LLM interface and management
- `orchestration/prompts/`: Template-based prompts organized by component
- `orchestration/config.py`: Comprehensive system configuration
- `orchestration/ai_types.py`: Core type definitions (replaces deprecated `types.py`)
- `tests/`: Component tests with deterministic output validation

## Coding Standards and Guidelines

### Type Hints Policy

```python
# ✅ Required: All public functions must have complete type hints
from typing import Optional, Dict, List, Any
from pydantic import BaseModel

def process_task(
    task_id: str,
    config: Dict[str, Any],
    timeout: float = 30.0
) -> Optional[TaskResult]:
    """Process a task with the given configuration.

    Args:
        task_id: Unique identifier for the task
        config: Configuration parameters
        timeout: Maximum execution time in seconds

    Returns:
        Task result if successful, None if failed

    Raises:
        TaskProcessingError: If task processing fails
    """
    pass

# ✅ Use Pydantic models for data validation
class TaskConfig(BaseModel):
    task_type: str
    priority: int = 1
    parameters: Dict[str, Any] = {}
```

### Error Handling Patterns

```python
# ✅ Specific exception classes with context
class ComponentError(Exception):
    """Base exception for component errors."""
    pass

class TemplateNotFoundError(ComponentError):
    """Raised when a required template is not found."""

    def __init__(self, template_id: str, available_templates: List[str]):
        self.template_id = template_id
        self.available_templates = available_templates
        super().__init__(f"Template '{template_id}' not found")

# ✅ Proper logging with context
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def safe_llm_call(prompt: str) -> Optional[str]:
    """Make a safe LLM call with proper error handling."""
    try:
        result = await llm_client.generate(prompt)
        logger.info(f"LLM call successful, response length: {len(result)}")
        return result
    except TimeoutError as e:
        logger.warning(f"LLM call timed out: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error in LLM call: {e}")
        raise LLMError(f"Failed to generate response: {e}") from e
```

### Component Implementation Guidelines

```python
# ✅ Always inherit from BaseAIComponent
from orchestration.components.base import BaseAIComponent
from orchestration.ai_types import OrchestrationMessage, MessageType

class MyComponent(BaseAIComponent):
    """Example component following the standard pattern."""

    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        super().__init__(session)
        self.llm_manager = llm_manager
        self.component_type = ComponentType.WORKER

    async def process_message(
        self,
        message: OrchestrationMessage
    ) -> List[OrchestrationMessage]:
        """Process incoming messages with proper validation."""
        if message.type != MessageType.COMMAND:
            return [self._create_error_message(
                message.sender,
                f"Unsupported message type: {message.type}"
            )]

        try:
            return await self._handle_command(message)
        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return [self._create_error_message(
                message.sender,
                f"Command processing failed: {str(e)}"
            )]
```

### Template and Prompt Management

```python
# ✅ Consistent template ID construction
def get_template_id(component: str, task_type: str, operation: str) -> str:
    """Construct standardized template ID."""
    return f"{component}/{task_type}_{operation}"

# ✅ Template variables validation
from typing import Dict, Any, Set

def validate_template_variables(
    variables: Dict[str, Any],
    required_vars: Set[str]
) -> None:
    """Validate that all required template variables are present."""
    missing = required_vars - set(variables.keys())
    if missing:
        raise ValueError(f"Missing required template variables: {missing}")
```

### Testing Requirements

```python
# ✅ All tests must be async-compatible and use proper fixtures
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.fixture
async def mock_llm_manager():
    """Create a mock LLM manager for testing."""
    manager = Mock()
    manager.generate_with_template = AsyncMock(return_value="test response")
    return manager

@pytest.mark.asyncio
async def test_component_message_processing(mock_llm_manager):
    """Test component message processing with deterministic output."""
    # Given
    session = Session(id="test-session")
    component = MyComponent(session, mock_llm_manager)
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=ComponentType.DIRECTOR,
        receiver=ComponentType.WORKER,
        content={"action": "test_action"},
        session_id="test-session"
    )

    # When
    result = await component.process_message(message)

    # Then
    assert len(result) == 1
    assert result[0].type == MessageType.RESPONSE
    mock_llm_manager.generate_with_template.assert_called_once()
```

## Development Notes

### Error Handling

- Component failures are handled gracefully with retry mechanisms
- LLM timeout/loading issues have built-in retry with exponential backoff
- Missing templates provide "close match" suggestions via `llm_manager.py`
- Always use specific exception types with meaningful error messages

### Testing Strategy

- Tests validate deterministic behavior by running identical inputs twice and comparing outputs
- Particularly important for `temperature=0.0` components
- Use `pytest` markers for test categorization: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.ai`
- Maintain >80% code coverage

### Configuration

- Environment variables prefixed with `ORCHESTRATOR_`
- Default settings in `config.py` cover timeouts, retry counts, model parameters
- Mode-specific parameters (creative vs coding vs research)
- Use Pydantic for all configuration models

### Code Quality Requirements

- All code must pass `ruff check` and `ruff format`
- Type checking with `mypy` must pass
- Security scanning with `bandit` must pass
- Use `pre-commit` hooks for automatic quality checks

### Performance Considerations

- Use async/await for I/O operations
- Implement proper connection pooling for LLM clients
- Cache template loading results
- Monitor memory usage in long-running processes

### Documentation Standards

- Use Google-style docstrings for all public functions
- Include type information in docstrings when not obvious from type hints
- Document complex algorithms and business logic
- Keep README.md and ARCHITECTURE.md up to date
