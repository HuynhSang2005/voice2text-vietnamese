"""
Unit Tests for API Dependencies

Tests FastAPI dependency functions and their integration with DI container.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import (
    get_di_container,
    get_db_session,
    get_session_service,
    get_audio_service,
    get_transcribe_audio_use_case,
    get_get_history_use_case,
    get_get_history_item_use_case,
    get_delete_history_item_use_case,
    get_delete_all_history_use_case,
    get_get_model_status_use_case,
    get_switch_model_use_case,
    get_list_available_models_use_case,
    get_moderate_content_use_case,
    get_get_moderation_status_use_case,
    validate_session,
    get_current_user,
    require_auth,
    rate_limit,
)
from app.infrastructure.config.container import Container


# ============================================================================
# Tests for Core Dependencies
# ============================================================================

def test_get_di_container_returns_container():
    """Test that get_di_container returns a Container instance"""
    container = get_di_container()
    # Check that container has expected providers
    assert hasattr(container, 'session_service')
    assert hasattr(container, 'audio_service')
    assert hasattr(container, 'transcribe_audio_use_case')


@pytest.mark.asyncio
async def test_get_db_session_yields_session():
    """Test that get_db_session yields an AsyncSession"""
    async for session in get_db_session():
        assert isinstance(session, AsyncSession)
        break  # Only test first yield


# ============================================================================
# Tests for Service Dependencies
# ============================================================================

def test_get_session_service_returns_service():
    """Test that get_session_service returns SessionService"""
    container = get_di_container()
    service = get_session_service(container)
    
    assert service is not None
    # Verify it's the right type
    assert service.__class__.__name__ == 'SessionService'


def test_get_audio_service_returns_service():
    """Test that get_audio_service returns AudioService"""
    container = get_di_container()
    service = get_audio_service(container)
    
    assert service is not None
    # Verify it's the right type
    assert service.__class__.__name__ == 'AudioService'


# ============================================================================
# Tests for Use Case Dependencies - Transcription
# ============================================================================

@pytest.mark.skip(reason="Workers need real model files - tested in integration tests")
def test_get_transcribe_audio_use_case_returns_use_case():
    """Test that get_transcribe_audio_use_case returns TranscribeAudioUseCase"""
    container = get_di_container()
    use_case = get_transcribe_audio_use_case(container)
    
    assert use_case is not None
    assert hasattr(use_case, 'execute')


# ============================================================================
# Tests for Use Case Dependencies - History Management
# ============================================================================

@pytest.mark.skip(reason="Use case has async dependencies - tested in integration tests")
def test_get_get_history_use_case_returns_use_case():
    """Test that get_get_history_use_case returns GetHistoryUseCase"""
    container = get_di_container()
    use_case = get_get_history_use_case(container)
    
    # Note: GetHistoryUseCase.execute returns a coroutine/Future
    assert use_case is not None
    assert use_case.__class__.__name__ == 'GetHistoryUseCase'


@pytest.mark.skip(reason="Use case has async dependencies - tested in integration tests")
def test_get_get_history_item_use_case_returns_use_case():
    """Test that get_get_history_item_use_case returns GetHistoryItemUseCase"""
    container = get_di_container()
    use_case = get_get_history_item_use_case(container)
    
    assert use_case is not None
    assert use_case.__class__.__name__ == 'GetHistoryItemUseCase'


@pytest.mark.skip(reason="Use case has async dependencies - tested in integration tests")
def test_get_delete_history_item_use_case_returns_use_case():
    """Test that get_delete_history_item_use_case returns DeleteHistoryItemUseCase"""
    container = get_di_container()
    use_case = get_delete_history_item_use_case(container)
    
    assert use_case is not None
    assert use_case.__class__.__name__ == 'DeleteHistoryItemUseCase'


@pytest.mark.skip(reason="Use case has async dependencies - tested in integration tests")
def test_get_delete_all_history_use_case_returns_use_case():
    """Test that get_delete_all_history_use_case returns DeleteAllHistoryUseCase"""
    container = get_di_container()
    use_case = get_delete_all_history_use_case(container)
    
    assert use_case is not None
    assert use_case.__class__.__name__ == 'DeleteAllHistoryUseCase'


# ============================================================================
# Tests for Use Case Dependencies - Model Management
# ============================================================================

@pytest.mark.skip(reason="Workers need real model files - tested in integration tests")
def test_get_get_model_status_use_case_returns_use_case():
    """Test that get_get_model_status_use_case returns GetModelStatusUseCase"""
    container = get_di_container()
    use_case = get_get_model_status_use_case(container)
    
    assert use_case is not None
    assert hasattr(use_case, 'execute')


@pytest.mark.skip(reason="Workers need real model files - tested in integration tests")
def test_get_switch_model_use_case_returns_use_case():
    """Test that get_switch_model_use_case returns SwitchModelUseCase"""
    container = get_di_container()
    use_case = get_switch_model_use_case(container)
    
    assert use_case is not None
    assert hasattr(use_case, 'execute')


def test_get_list_available_models_use_case_returns_use_case():
    """Test that get_list_available_models_use_case returns ListAvailableModelsUseCase"""
    container = get_di_container()
    use_case = get_list_available_models_use_case(container)
    
    assert use_case is not None
    assert use_case.__class__.__name__ == 'ListAvailableModelsUseCase'


# ============================================================================
# Tests for Use Case Dependencies - Moderation
# ============================================================================

@pytest.mark.skip(reason="Workers need real model files - tested in integration tests")
def test_get_moderate_content_use_case_returns_use_case():
    """Test that get_moderate_content_use_case returns ModerateContentUseCase"""
    container = get_di_container()
    use_case = get_moderate_content_use_case(container)
    
    assert use_case is not None
    assert hasattr(use_case, 'execute')


@pytest.mark.skip(reason="Workers need real model files - tested in integration tests")
def test_get_get_moderation_status_use_case_returns_use_case():
    """Test that get_get_moderation_status_use_case returns GetModerationStatusUseCase"""
    container = get_di_container()
    use_case = get_get_moderation_status_use_case(container)
    
    assert use_case is not None
    assert hasattr(use_case, 'execute')


# ============================================================================
# Tests for Session Validation
# ============================================================================

@pytest.mark.asyncio
async def test_validate_session_with_valid_session_id():
    """Test validate_session with a valid session ID"""
    mock_session_service = Mock()
    
    result = await validate_session(
        x_session_id="test-session-123",
        session_service=mock_session_service
    )
    
    assert result == "test-session-123"


@pytest.mark.asyncio
async def test_validate_session_without_session_id():
    """Test validate_session without a session ID returns None"""
    mock_session_service = Mock()
    
    result = await validate_session(
        x_session_id=None,
        session_service=mock_session_service
    )
    
    assert result is None


# ============================================================================
# Tests for Authentication (Future Placeholder)
# ============================================================================

@pytest.mark.asyncio
async def test_get_current_user_without_auth():
    """Test get_current_user returns None when no auth provided"""
    result = await get_current_user(authorization=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_with_bearer_token():
    """Test get_current_user with Bearer token (placeholder)"""
    result = await get_current_user(authorization="Bearer test-token")
    # Currently returns None (placeholder implementation)
    assert result is None


@pytest.mark.asyncio
async def test_require_auth_without_user_raises_401():
    """Test require_auth raises 401 when user is None"""
    with pytest.raises(HTTPException) as exc_info:
        await require_auth(user=None)
    
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_auth_with_user_returns_user():
    """Test require_auth returns user when authenticated"""
    mock_user = {"id": "user123", "email": "test@example.com"}
    
    result = await require_auth(user=mock_user)
    
    assert result == mock_user


# ============================================================================
# Tests for Rate Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limit_allows_requests_within_limit():
    """Test rate_limit allows requests within the limit"""
    mock_request = Mock(spec=Request)
    mock_request.client = Mock(host="192.168.1.1")
    
    # Should not raise for first request
    await rate_limit(mock_request, max_requests=10, window_seconds=60)
    
    # Should allow multiple requests within limit
    for _ in range(5):
        await rate_limit(mock_request, max_requests=10, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limit_blocks_requests_exceeding_limit():
    """Test rate_limit blocks requests exceeding the limit"""
    mock_request = Mock(spec=Request)
    mock_request.client = Mock(host="192.168.1.2")
    
    # Clear any existing rate limit data for this IP
    from app.api import deps
    deps._rate_limit_storage.clear()
    
    # Make requests up to the limit
    max_requests = 5
    for i in range(max_requests):
        await rate_limit(mock_request, max_requests=max_requests, window_seconds=60)
    
    # Next request should be blocked
    with pytest.raises(HTTPException) as exc_info:
        await rate_limit(mock_request, max_requests=max_requests, window_seconds=60)
    
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rate_limit_different_ips_tracked_separately():
    """Test rate_limit tracks different IPs separately"""
    mock_request_1 = Mock(spec=Request)
    mock_request_1.client = Mock(host="192.168.1.3")
    
    mock_request_2 = Mock(spec=Request)
    mock_request_2.client = Mock(host="192.168.1.4")
    
    # Clear rate limit storage
    from app.api import deps
    deps._rate_limit_storage.clear()
    
    max_requests = 3
    
    # Make requests from IP 1 up to limit
    for _ in range(max_requests):
        await rate_limit(mock_request_1, max_requests=max_requests, window_seconds=60)
    
    # IP 2 should still be able to make requests
    await rate_limit(mock_request_2, max_requests=max_requests, window_seconds=60)
    
    # IP 1 should be blocked
    with pytest.raises(HTTPException) as exc_info:
        await rate_limit(mock_request_1, max_requests=max_requests, window_seconds=60)
    
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_window_expires():
    """Test rate_limit window expiration"""
    import time
    from app.api import deps
    
    mock_request = Mock(spec=Request)
    mock_request.client = Mock(host="192.168.1.5")
    
    # Clear rate limit storage
    deps._rate_limit_storage.clear()
    
    max_requests = 2
    window_seconds = 1  # 1 second window for testing
    
    # Make requests up to limit
    for _ in range(max_requests):
        await rate_limit(mock_request, max_requests=max_requests, window_seconds=window_seconds)
    
    # Should be blocked
    with pytest.raises(HTTPException):
        await rate_limit(mock_request, max_requests=max_requests, window_seconds=window_seconds)
    
    # Wait for window to expire
    time.sleep(window_seconds + 0.1)
    
    # Should allow requests again
    await rate_limit(mock_request, max_requests=max_requests, window_seconds=window_seconds)


@pytest.mark.asyncio
async def test_rate_limit_handles_missing_client_info():
    """Test rate_limit handles requests without client info"""
    mock_request = Mock(spec=Request)
    mock_request.client = None  # No client info
    
    # Should not raise exception, uses "unknown" as key
    await rate_limit(mock_request, max_requests=10, window_seconds=60)
