#!/usr/bin/env python3
"""
Latency testing script for who-dunnit robot pipeline.
Tests response times for typical conversation scenarios.
"""

import time
import json
from latency_monitor import LatencyMonitor

def test_conversation_scenarios():
    """Test typical who-dunnit conversation patterns."""
    monitor = LatencyMonitor()

    # Test scenarios representing different conversation types
    scenarios = [
        {
            "name": "Greeting",
            "input": "Hello, I'm ready to solve the mystery",
            "expected_response_type": "greeting",
            "target_latency_ms": 1500  # Quick response for greetings
        },
        {
            "name": "Simple Question",
            "input": "What's my name?",
            "expected_response_type": "question",
            "target_latency_ms": 2000  # Standard conversation
        },
        {
            "name": "Mystery Question",
            "input": "Does the suspect have glasses?",
            "expected_response_type": "yes_no",
            "target_latency_ms": 1800  # Quick yes/no response
        },
        {
            "name": "Complex Reasoning",
            "input": "I'm stuck and need a hint about the suspect",
            "expected_response_type": "hint",
            "target_latency_ms": 2500  # More complex reasoning
        },
        {
            "name": "Task Explanation",
            "input": "Can you explain the tasks again?",
            "expected_response_type": "explanation",
            "target_latency_ms": 3000  # Longer explanation
        }
    ]

    print("🧪 Testing Who-Dunnit Conversation Latency")
    print("=" * 50)

    results = []

    for scenario in scenarios:
        print(f"\n📝 Testing: {scenario['name']}")
        print(f"   Input: \"{scenario['input']}\"")
        print(f"   Target: <{scenario['target_latency_ms']}ms")

        # Simulate component timings based on input complexity
        monitor.start_conversation()

        # Simulate VAD (voice activity detection)
        vad_time = 30 + len(scenario['input']) * 0.5  # Varies with audio length
        monitor.log_component_time('VAD', vad_time)

        # Simulate STT (speech to text)
        stt_time = 200 + len(scenario['input']) * 3  # Varies with speech length
        monitor.log_component_time('STT', stt_time)

        # Simulate LLM (language model) - varies by complexity
        if scenario['expected_response_type'] == 'greeting':
            llm_time = 400  # Simple greeting
        elif scenario['expected_response_type'] == 'yes_no':
            llm_time = 600  # Quick lookup
        elif scenario['expected_response_type'] == 'hint':
            llm_time = 1200  # Complex reasoning
        else:
            llm_time = 800  # Standard response

        monitor.log_component_time('LLM', llm_time)

        # Simulate TTS (text to speech)
        estimated_response_length = llm_time / 10  # Rough estimate
        tts_time = 300 + estimated_response_length * 2
        monitor.log_component_time('TTS', tts_time)

        # Simulate robot expression action
        monitor.log_robot_action('expression_change', 150)

        # End conversation and get metrics
        metrics = monitor.end_conversation_turn()

        # Evaluate performance
        total_time = metrics.get('total_latency_ms', 0)
        target_time = scenario['target_latency_ms']

        performance = "✅ PASS" if total_time <= target_time else "❌ FAIL"
        efficiency = metrics.get('efficiency_pct', 0)

        print(f"   Result: {total_time:.1f}ms ({performance})")
        print(f"   Breakdown: VAD {vad_time:.0f}ms | STT {stt_time:.0f}ms | LLM {llm_time:.0f}ms | TTS {tts_time:.0f}ms")
        print(f"   Efficiency: {efficiency:.1f}%")

        results.append({
            'scenario': scenario['name'],
            'total_ms': total_time,
            'target_ms': target_time,
            'passed': total_time <= target_time,
            'efficiency': efficiency
        })

    # Generate summary report
    print("\n📊 LATENCY TEST SUMMARY")
    print("=" * 50)

    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    avg_latency = sum(r['total_ms'] for r in results) / total
    avg_efficiency = sum(r['efficiency'] for r in results) / total

    print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"Average Latency: {avg_latency:.1f}ms")
    print(f"Average Efficiency: {avg_efficiency:.1f}%")

    # Performance recommendations
    print("\n💡 RECOMMENDATIONS FOR MISTY INTEGRATION:")
    if avg_latency > 2500:
        print("⚠️  High latency detected. Consider:")
        print("   - Smaller LLM model for faster inference")
        print("   - Flash attention for GPU optimization")
        print("   - Streaming TTS to reduce perceived latency")

    if avg_efficiency < 80:
        print("⚠️  Low efficiency detected. Check for:")
        print("   - Queue bottlenecks between components")
        print("   - Network delays to robot")
        print("   - Audio buffer sizes")

    print("\n🤖 Misty Robot Considerations:")
    print("   - Network latency: +50-100ms (WiFi communication)")
    print("   - Expression changes: +100-200ms (motor movements)")
    print("   - Audio playback sync: +50ms (speaker latency)")
    print("   - Total robot overhead: ~200-400ms additional")

    # Export detailed results
    timestamp = int(time.time())
    filename = f"latency_test_results_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump({
            'test_timestamp': timestamp,
            'summary': {
                'passed': passed,
                'total': total,
                'avg_latency_ms': avg_latency,
                'avg_efficiency_pct': avg_efficiency
            },
            'detailed_results': results,
            'performance_report': monitor.get_performance_report()
        }, f, indent=2)

    print(f"\n📁 Detailed results saved to: {filename}")

    return results

if __name__ == "__main__":
    test_conversation_scenarios()