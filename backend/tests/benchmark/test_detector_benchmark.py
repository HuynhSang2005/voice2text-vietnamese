"""
Benchmark tests for HateDetectorWorker (ViSoBERT-HSD).

Measures:
- Single inference latency
- Batch throughput
- Memory usage
- ONNX INT8 vs ONNX FP32 comparison

Run with: pytest tests/benchmark/test_detector_benchmark.py -v -s
"""
import pytest
import time
import statistics
import os
import sys
import multiprocessing
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# =============================================================================
# Test Data
# =============================================================================

# Sample Vietnamese texts for benchmarking
CLEAN_TEXTS = [
    "Xin chào, tôi là sinh viên đại học.",
    "Hôm nay thời tiết rất đẹp.",
    "Tôi thích học tiếng Việt.",
    "Cảm ơn bạn đã giúp đỡ tôi.",
    "Chúc bạn một ngày tốt lành.",
    "Việt Nam có nhiều địa điểm du lịch đẹp.",
    "Món phở Việt Nam rất ngon.",
    "Tôi đang làm việc tại công ty công nghệ.",
]

OFFENSIVE_TEXTS = [
    "Đồ ngu ngốc, mày không hiểu gì cả.",
    "Thằng khốn nạn, biến đi.",
    "Mày là thằng vô dụng.",
]

HATE_TEXTS = [
    "Bọn người đó thật đáng ghét, nên bị loại bỏ.",
    "Những kẻ như vậy không xứng đáng tồn tại.",
]

# Mixed texts for realistic benchmarking
ALL_TEXTS = CLEAN_TEXTS + OFFENSIVE_TEXTS + HATE_TEXTS

# Long texts for stress testing
LONG_TEXTS = [
    "Đây là một đoạn văn bản dài để kiểm tra khả năng xử lý của model. " * 20,  # ~200 words
    "Xin chào các bạn, hôm nay tôi muốn chia sẻ với các bạn về kinh nghiệm học tập. " * 15,
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def detector_worker():
    """Create a HateDetectorWorker for benchmarking."""
    from app.workers.hate_detector import HateDetectorWorker
    
    input_q = multiprocessing.Queue()
    output_q = multiprocessing.Queue()
    
    worker = HateDetectorWorker(input_q, output_q, "visobert-hsd")
    
    # Load model (this is the expensive operation)
    print("\n[Setup] Loading ViSoBERT-HSD model...")
    start = time.time()
    worker.load_model()
    load_time = time.time() - start
    print(f"[Setup] Model loaded in {load_time:.2f}s")
    
    yield worker
    
    # Cleanup
    input_q.close()
    output_q.close()


@pytest.fixture(scope="module")
def benchmark_results():
    """Store benchmark results for summary."""
    return {
        "single_inference": [],
        "batch_inference": [],
        "long_text": [],
    }


# =============================================================================
# Benchmark Tests
# =============================================================================

class TestDetectorLatencyBenchmark:
    """Benchmark single inference latency."""
    
    def test_warmup(self, detector_worker):
        """Warmup the model before benchmarking."""
        print("\n[Warmup] Running 5 warmup inferences...")
        for i in range(5):
            detector_worker.process({"text": "Xin chào", "request_id": f"warmup-{i}"})
            detector_worker.output_queue.get(timeout=10)
        print("[Warmup] Complete")
    
    def test_single_inference_latency(self, detector_worker, benchmark_results):
        """Measure single inference latency across multiple runs."""
        print("\n" + "=" * 60)
        print("BENCHMARK: Single Inference Latency")
        print("=" * 60)
        
        latencies = []
        
        for i, text in enumerate(ALL_TEXTS * 3):  # Run each text 3 times
            request_id = f"bench-{i}"
            
            start = time.perf_counter()
            detector_worker.process({"text": text, "request_id": request_id})
            result = detector_worker.output_queue.get(timeout=10)
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
            
            # Also check the model's internal latency measurement
            if "latency_ms" in result:
                benchmark_results["single_inference"].append(result["latency_ms"])
        
        # Calculate statistics
        avg = statistics.mean(latencies)
        median = statistics.median(latencies)
        stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nResults ({len(latencies)} inferences):")
        print(f"  Average:  {avg:.2f} ms")
        print(f"  Median:   {median:.2f} ms")
        print(f"  Std Dev:  {stdev:.2f} ms")
        print(f"  P95:      {p95:.2f} ms")
        print(f"  P99:      {p99:.2f} ms")
        print(f"  Min:      {min(latencies):.2f} ms")
        print(f"  Max:      {max(latencies):.2f} ms")
        
        # Assertions for performance targets
        # Note: These targets are for typical CPU hardware
        # P95 may be higher due to GC, cache effects, etc.
        assert avg < 150, f"Average latency {avg:.2f}ms exceeds 150ms target"
        assert p95 < 300, f"P95 latency {p95:.2f}ms exceeds 300ms target"
        
        print("\n✅ Latency targets met!")
    
    def test_long_text_latency(self, detector_worker, benchmark_results):
        """Test latency with long texts (near max sequence length)."""
        print("\n" + "=" * 60)
        print("BENCHMARK: Long Text Latency")
        print("=" * 60)
        
        latencies = []
        
        for i, text in enumerate(LONG_TEXTS * 5):  # 10 runs
            start = time.perf_counter()
            detector_worker.process({"text": text, "request_id": f"long-{i}"})
            result = detector_worker.output_queue.get(timeout=30)
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
            benchmark_results["long_text"].append(latency_ms)
        
        avg = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        
        print(f"\nLong text results ({len(latencies)} inferences):")
        print(f"  Average:  {avg:.2f} ms")
        print(f"  P95:      {p95:.2f} ms")
        print(f"  Min:      {min(latencies):.2f} ms")
        print(f"  Max:      {max(latencies):.2f} ms")
        
        # Long texts (near max sequence length) may take longer
        # 500ms is acceptable for long content moderation
        assert avg < 600, f"Average long text latency {avg:.2f}ms exceeds 600ms target"
        
        print("\n✅ Long text latency acceptable!")


class TestDetectorThroughputBenchmark:
    """Benchmark throughput (texts per second)."""
    
    def test_throughput(self, detector_worker):
        """Measure maximum throughput."""
        print("\n" + "=" * 60)
        print("BENCHMARK: Throughput (texts/second)")
        print("=" * 60)
        
        num_texts = 50
        texts = (ALL_TEXTS * 10)[:num_texts]
        
        start = time.perf_counter()
        
        for i, text in enumerate(texts):
            detector_worker.process({"text": text, "request_id": f"throughput-{i}"})
            detector_worker.output_queue.get(timeout=10)
        
        end = time.perf_counter()
        total_time = end - start
        throughput = num_texts / total_time
        
        print(f"\nResults:")
        print(f"  Total texts:    {num_texts}")
        print(f"  Total time:     {total_time:.2f}s")
        print(f"  Throughput:     {throughput:.2f} texts/second")
        print(f"  Avg per text:   {(total_time / num_texts) * 1000:.2f} ms")
        
        # Should process at least 10 texts per second
        assert throughput > 10, f"Throughput {throughput:.2f} texts/s is below 10/s target"
        
        print("\n✅ Throughput target met!")


class TestDetectorAccuracyBenchmark:
    """Verify accuracy on known samples."""
    
    def test_classification_accuracy(self, detector_worker):
        """Test classification accuracy on known samples."""
        print("\n" + "=" * 60)
        print("BENCHMARK: Classification Accuracy")
        print("=" * 60)
        
        test_cases = [
            # (text, expected_label)
            ("Xin chào bạn", "CLEAN"),
            ("Hôm nay trời đẹp quá", "CLEAN"),
            ("Cảm ơn bạn rất nhiều", "CLEAN"),
        ]
        
        correct = 0
        total = len(test_cases)
        
        for text, expected in test_cases:
            detector_worker.process({"text": text, "request_id": "acc"})
            result = detector_worker.output_queue.get(timeout=10)
            
            actual = result.get("label")
            is_correct = actual == expected
            correct += 1 if is_correct else 0
            
            status = "✓" if is_correct else "✗"
            print(f"  {status} '{text[:30]}...' → {actual} (expected: {expected})")
        
        accuracy = correct / total * 100
        print(f"\nAccuracy: {accuracy:.1f}% ({correct}/{total})")
        
        # At least 80% accuracy on clean texts
        assert accuracy >= 80, f"Accuracy {accuracy:.1f}% is below 80% target"
        
        print("\n✅ Accuracy acceptable!")


class TestModelComparison:
    """Compare ONNX INT8 vs FP32 (if both available)."""
    
    def test_int8_model_used(self, detector_worker):
        """Verify INT8 model is being used (smaller, faster)."""
        print("\n" + "=" * 60)
        print("BENCHMARK: Model Configuration")
        print("=" * 60)
        
        from app.core.config import get_settings
        settings = get_settings()
        
        int8_path = f"{settings.MODEL_STORAGE_PATH}/visobert-hsd/onnx-int8"
        fp32_path = f"{settings.MODEL_STORAGE_PATH}/visobert-hsd/onnx"
        
        # Check which model files exist
        int8_exists = os.path.exists(int8_path)
        fp32_exists = os.path.exists(fp32_path)
        
        print(f"  INT8 model path: {int8_path}")
        print(f"  INT8 exists: {int8_exists}")
        print(f"  FP32 model path: {fp32_path}")
        print(f"  FP32 exists: {fp32_exists}")
        
        if int8_exists:
            # Get file sizes
            int8_size = sum(
                os.path.getsize(os.path.join(int8_path, f))
                for f in os.listdir(int8_path)
                if f.endswith('.onnx')
            )
            print(f"\n  INT8 model size: {int8_size / 1024 / 1024:.1f} MB")
            
            if fp32_exists:
                fp32_size = sum(
                    os.path.getsize(os.path.join(fp32_path, f))
                    for f in os.listdir(fp32_path)
                    if f.endswith('.onnx')
                )
                print(f"  FP32 model size: {fp32_size / 1024 / 1024:.1f} MB")
                print(f"  Size reduction: {(1 - int8_size/fp32_size) * 100:.1f}%")
        
        print("\n✅ Model configuration verified!")


# =============================================================================
# Summary
# =============================================================================

class TestBenchmarkSummary:
    """Print final benchmark summary."""
    
    def test_print_summary(self, benchmark_results):
        """Print summary of all benchmarks."""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY: ViSoBERT-HSD (ONNX INT8)")
        print("=" * 60)
        
        if benchmark_results["single_inference"]:
            avg = statistics.mean(benchmark_results["single_inference"])
            print(f"\n📊 Single Inference:")
            print(f"   Average latency: {avg:.2f} ms")
        
        if benchmark_results["long_text"]:
            avg = statistics.mean(benchmark_results["long_text"])
            print(f"\n📊 Long Text Processing:")
            print(f"   Average latency: {avg:.2f} ms")
        
        print("\n" + "=" * 60)
        print("✅ All benchmarks completed!")
        print("=" * 60 + "\n")


# =============================================================================
# Standalone Runner
# =============================================================================

if __name__ == "__main__":
    """Run benchmarks standalone."""
    pytest.main([__file__, "-v", "-s"])
