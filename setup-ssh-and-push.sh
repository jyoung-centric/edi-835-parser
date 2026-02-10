#!/bin/bash
# Setup SSH and push PR branch to GitHub

set -e

echo "🔧 Configuring Git to use SSH..."
git remote set-url origin git@github.com-edi-835-parser:jyoung-centric/edi-835-parser.git

echo ""
echo "🔐 Testing SSH connection to GitHub..."
if ssh -T git@github.com-edi-835-parser 2>&1 | grep -q "successfully authenticated"; then
    echo "✅ SSH connection successful!"
else
    echo "⚠️  SSH test output:"
    ssh -T git@github.com-edi-835-parser 2>&1 || true
fi

echo ""
echo "📤 Pushing branch to GitHub..."
git push -u origin fix/multi-transaction-db-insert

echo ""
echo "✅ Branch pushed successfully!"
echo ""
echo "📝 Create PR with:"
echo "   gh pr create --title \"Fix: Multiple transactions create separate DB records\" --body-file PR_DESCRIPTION.md"
echo ""
echo "Or visit:"
echo "   https://github.com/jyoung-centric/edi-835-parser/pull/new/fix/multi-transaction-db-insert"
