#!/bin/bash
# Emergency rollback to Phase 1 working version

echo "🚨 Rolling back to Phase 1 working version..."
echo ""
echo "This will:"
echo "  - Discard any uncommitted changes"
echo "  - Reset to the phase-1-working tag"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Rollback cancelled"
    exit 1
fi

echo ""
echo "Rolling back..."
git reset --hard phase-1-working

echo ""
echo "✅ Rolled back to Phase 1 working version!"
echo ""
echo "To start the app:"
echo "  python3 -m flask --app app run --host 0.0.0.0 --port 5001"

