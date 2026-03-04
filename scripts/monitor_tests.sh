#!/bin/bash
# Monitor E2E Test Progress

echo "======================================================"
echo "PageIndex E2E Test Monitor"
echo "======================================================"
echo ""

# Check if test is running
if pgrep -f "test_comprehensive.py" > /dev/null; then
    echo "✓ Test process is running (PID: $(pgrep -f test_comprehensive.py))"
else
    echo "✗ Test process is not running"
fi

echo ""
echo "--- Recent Log Activity ---"
tail -20 /workspace/PageIndexOllama/test_comprehensive_full.log | grep -E "Starting E2E test|✓|✗|STEP"

echo ""
echo "--- Test Progress ---"
completed=$(grep -c "E2E test completed" /workspace/PageIndexOllama/test_comprehensive_full.log 2>/dev/null || echo "0")
failed=$(grep -c "E2E test failed" /workspace/PageIndexOllama/test_comprehensive_full.log 2>/dev/null || echo "0")
echo "Completed: $completed"
echo "Failed: $failed"
echo "Total PDFs: 10"

echo ""
echo "--- GPU Status ---"
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "GPU info not available"

echo ""
echo "======================================================"
echo "To see live updates: tail -f test_comprehensive_full.log"
echo "To check reports: ls -lh tests/reports/"
echo "======================================================"
