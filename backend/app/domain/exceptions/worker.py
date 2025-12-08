"""Worker exception - Worker-related failures."""


class WorkerException(Exception):
    """
    Exception raised when a worker operation fails.

    This exception covers failures in worker lifecycle (start, stop),
    model loading, inference, or any worker-specific errors.

    Attributes:
        worker_type: Type of worker that failed ('transcription', 'moderation', 'status')
        message: Human-readable error message

    Example:
        ```python
        raise WorkerException(
            worker_type="transcription",
            message="Failed to load Zipformer model: file not found"
        )
        ```
    """

    def __init__(self, worker_type: str, message: str):
        """
        Initialize worker exception.

        Args:
            worker_type: Type of worker ('transcription', 'moderation', 'status')
            message: Error message describing the failure
        """
        self.worker_type = worker_type
        self.message = message
        super().__init__(f"Worker '{worker_type}' error: {message}")

    def __str__(self) -> str:
        """String representation of the exception."""
        return f"WorkerException(worker_type='{self.worker_type}', message='{self.message}')"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"WorkerException(worker_type={self.worker_type!r}, message={self.message!r})"
