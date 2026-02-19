#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/.claude/statusline.py"
SETTINGS="$HOME/.claude/settings.json"

cp statusline.py "$DEST"
echo "Copied statusline.py -> $DEST"

# Patch settings.json
if [ -f "$SETTINGS" ]; then
  python3 -c "
import json, sys
with open('$SETTINGS') as f:
    s = json.load(f)
s['statusLine'] = {'type': 'command', 'command': 'python3 ~/.claude/statusline.py'}
with open('$SETTINGS', 'w') as f:
    json.dump(s, f, indent=2)
print('Patched statusLine in $SETTINGS')
"
else
  mkdir -p "$(dirname "$SETTINGS")"
  echo '{"statusLine":{"type":"command","command":"python3 ~/.claude/statusline.py"}}' > "$SETTINGS"
  echo "Created $SETTINGS"
fi

echo ""
echo "Done. Restart Claude Code to see the status line."
echo ""
echo "NOTE: Your OAuth token needs the user:profile scope."
echo "If rate limits show '--', run: claude auth logout && claude auth login"
