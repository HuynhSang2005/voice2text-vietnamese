"""
Test imports for Phase 2.1 interfaces.
"""
import pytest


def test_worker_interfaces_import():
    """Test that worker interfaces can be imported."""
    from app.application.interfaces.workers import (
        ITranscriptionWorker,
        IModerationWorker,
        IWorkerManager,
    )
    
    assert ITranscriptionWorker is not None
    assert IModerationWorker is not None
    assert IWorkerManager is not None


def test_cache_interfaces_import():
    """Test that cache interfaces can be imported."""
    from app.application.interfaces.cache import ICache, ICacheFactory
    
    assert ICache is not None
    assert ICacheFactory is not None


def test_central_imports():
    """Test that all interfaces can be imported from central module."""
    from app.application.interfaces import (
        ITranscriptionRepository,
        ISessionRepository,
        ITranscriptionWorker,
        IModerationWorker,
        IWorkerManager,
        ICache,
        ICacheFactory,
    )
    
    # Verify all imports worked
    assert ITranscriptionRepository is not None
    assert ISessionRepository is not None
    assert ITranscriptionWorker is not None
    assert IModerationWorker is not None
    assert IWorkerManager is not None
    assert ICache is not None
    assert ICacheFactory is not None


def test_worker_protocol_structure():
    """Test that worker protocols have expected methods."""
    from app.application.interfaces.workers import ITranscriptionWorker
    
    # Protocol should have these methods defined
    assert hasattr(ITranscriptionWorker, 'process_audio_stream')
    assert hasattr(ITranscriptionWorker, 'start')
    assert hasattr(ITranscriptionWorker, 'stop')
    assert hasattr(ITranscriptionWorker, 'is_ready')


def test_cache_protocol_structure():
    """Test that cache protocol has expected methods."""
    from app.application.interfaces.cache import ICache
    
    # Protocol should have these methods defined
    assert hasattr(ICache, 'get')
    assert hasattr(ICache, 'set')
    assert hasattr(ICache, 'delete')
    assert hasattr(ICache, 'exists')
    assert hasattr(ICache, 'expire')
    assert hasattr(ICache, 'clear')
    assert hasattr(ICache, 'get_ttl')
    assert hasattr(ICache, 'ping')
