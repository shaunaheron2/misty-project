#!/usr/bin/env python3
"""
Latency Monitoring System for Speech-to-Speech Pipeline
Tracks component-level and end-to-end timing for robotics applications.
"""

import time
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import statistics

logger = logging.getLogger(__name__)

@dataclass
class LatencyMeasurement:
    """Single latency measurement with context."""
    component: str
    duration_ms: float
    timestamp: float
    input_size: Optional[int] = None  # Audio samples, text length, etc.
    model_info: Optional[str] = None  # Model name/size
    action: Optional[str] = None  # Robot action type

class LatencyMonitor:
    """
    Comprehensive latency monitoring for speech-to-speech pipeline.

    Tracks:
    - Component-level timing (VAD, STT, LLM, TTS)
    - End-to-end conversation latency
    - Robot-specific delays (network, actions)
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.conversation_start: Optional[float] = None
        self.current_turn: Dict[str, float] = {}

    def start_conversation(self):
        """Mark the start of a new conversation turn."""
        self.conversation_start = time.time()
        self.current_turn = {}
        logger.info("🎯 Starting conversation turn")

    def log_component_time(self, component: str, duration_ms: float, **kwargs):
        """Log timing for a specific pipeline component."""
        # Filter kwargs to only include valid LatencyMeasurement fields
        valid_fields = {'input_size', 'model_info', 'action'}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}

        measurement = LatencyMeasurement(
            component=component,
            duration_ms=duration_ms,
            timestamp=time.time(),
            **filtered_kwargs
        )

        self.measurements[component].append(measurement)
        self.current_turn[component] = duration_ms

        logger.info(f"⏱️  {component}: {duration_ms:.1f}ms")

    def end_conversation_turn(self) -> Dict[str, float]:
        """Calculate and log end-to-end conversation metrics."""
        if not self.conversation_start:
            return {}

        total_time = (time.time() - self.conversation_start) * 1000

        # Component breakdown
        vad_time = self.current_turn.get('VAD', 0)
        stt_time = self.current_turn.get('STT', 0)
        llm_time = self.current_turn.get('LLM', 0)
        tts_time = self.current_turn.get('TTS', 0)
        robot_time = self.current_turn.get('ROBOT', 0)  # For Misty integration

        # Calculate pipeline efficiency
        processing_time = vad_time + stt_time + llm_time + tts_time + robot_time
        overhead_time = total_time - processing_time

        metrics = {
            'total_latency_ms': total_time,
            'vad_ms': vad_time,
            'stt_ms': stt_time,
            'llm_ms': llm_time,
            'tts_ms': tts_time,
            'robot_ms': robot_time,
            'processing_ms': processing_time,
            'overhead_ms': overhead_time,
            'efficiency_pct': (processing_time / total_time) * 100 if total_time > 0 else 0
        }

        # Log results
        logger.info("🏁 Conversation turn complete:")
        logger.info(f"   Total: {total_time:.1f}ms")
        logger.info(f"   VAD: {vad_time:.1f}ms | STT: {stt_time:.1f}ms | LLM: {llm_time:.1f}ms | TTS: {tts_time:.1f}ms")
        if robot_time > 0:
            logger.info(f"   Robot: {robot_time:.1f}ms")
        logger.info(f"   Efficiency: {metrics['efficiency_pct']:.1f}%")

        # Store for analysis
        self.log_component_time('END_TO_END', total_time, **metrics)

        return metrics

    def get_component_stats(self, component: str) -> Dict[str, float]:
        """Get statistical summary for a component."""
        if component not in self.measurements or not self.measurements[component]:
            return {}

        times = [m.duration_ms for m in self.measurements[component]]

        return {
            'count': len(times),
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'std_ms': statistics.stdev(times) if len(times) > 1 else 0,
            'min_ms': min(times),
            'max_ms': max(times),
            'p95_ms': statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
        }

    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        report = {
            'timestamp': time.time(),
            'components': {}
        }

        for component in ['VAD', 'STT', 'LLM', 'TTS', 'ROBOT', 'END_TO_END']:
            stats = self.get_component_stats(component)
            if stats:
                report['components'][component] = stats

        # Add targets and recommendations
        report['targets'] = {
            'total_target_ms': 2000,  # 2 second target for natural conversation
            'llm_target_ms': 800,     # LLM should be fastest component
            'acceptable_total_ms': 3000
        }

        # Performance analysis
        if 'END_TO_END' in report['components']:
            avg_total = report['components']['END_TO_END']['mean_ms']
            report['performance_grade'] = self._grade_performance(avg_total)

        return report

    def _grade_performance(self, avg_total_ms: float) -> str:
        """Grade overall performance based on total latency."""
        if avg_total_ms < 1500:
            return "A+ (Excellent - Very responsive)"
        elif avg_total_ms < 2000:
            return "A (Good - Natural conversation)"
        elif avg_total_ms < 3000:
            return "B (Acceptable - Slight delay)"
        elif avg_total_ms < 5000:
            return "C (Slow - Noticeable delay)"
        else:
            return "D (Poor - Unusable for conversation)"

    def log_robot_action(self, action: str, duration_ms: float):
        """Log robot-specific actions (expressions, movements)."""
        self.log_component_time('ROBOT', duration_ms, action=action)
        logger.info(f"🤖 Robot action '{action}': {duration_ms:.1f}ms")

    def export_data(self, filename: str):
        """Export all measurements to JSON for analysis."""
        data = {
            'export_time': time.time(),
            'measurements': {}
        }

        for component, measurements in self.measurements.items():
            data['measurements'][component] = [asdict(m) for m in measurements]

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"📊 Exported latency data to {filename}")

# Global monitor instance
monitor = LatencyMonitor()

# Decorator for easy timing
def time_component(component_name: str):
    """Decorator to automatically time function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            monitor.log_component_time(component_name, duration_ms)
            return result
        return wrapper
    return decorator

if __name__ == "__main__":
    # Example usage
    monitor = LatencyMonitor()

    # Simulate a conversation
    monitor.start_conversation()
    monitor.log_component_time('VAD', 50)
    monitor.log_component_time('STT', 300)
    monitor.log_component_time('LLM', 800)
    monitor.log_component_time('TTS', 400)
    monitor.log_robot_action('hi', 200)

    metrics = monitor.end_conversation_turn()

    # Generate report
    report = monitor.get_performance_report()
    print(json.dumps(report, indent=2))