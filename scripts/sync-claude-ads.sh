#!/usr/bin/env bash
# sync-claude-ads.sh — pull the latest claude-ads from upstream into the vendored copy.
#
# Run from the Mad-Minds repo root:
#   bash scripts/sync-claude-ads.sh
#
# Then review the diff, bump the marketplace + plugin versions, commit, push.
# Mirrors what was vendored when the plugin was first added (see claude-ads/NOTICE.md).

set -euo pipefail

UPSTREAM=https://github.com/AgriciDaniel/claude-ads.git
TMP=$(mktemp -d)
DST="$(cd "$(dirname "$0")/.." && pwd)/claude-ads"

if [[ ! -d "$DST" ]]; then
  echo "Error: $DST does not exist. Run this script from the Mad-Minds repo root." >&2
  exit 1
fi

echo "Cloning upstream into $TMP ..."
git clone --depth 1 "$UPSTREAM" "$TMP/claude-ads" > /dev/null 2>&1

COMMIT=$(cd "$TMP/claude-ads" && git rev-parse HEAD)
DATE=$(cd "$TMP/claude-ads" && git log -1 --format=%cd --date=short)
UPSTREAM_VERSION=$(grep -m1 '"version"' "$TMP/claude-ads/.claude-plugin/plugin.json" | sed 's/[^"]*"version"[^"]*"\([^"]*\)".*/\1/')

echo "Upstream commit: $COMMIT ($DATE)"
echo "Upstream version: $UPSTREAM_VERSION"

# Preserve our NOTICE.md
NOTICE=$(cat "$DST/NOTICE.md" 2>/dev/null || true)

# Wipe + re-copy minimal runtime set
rm -rf "$DST"
mkdir -p "$DST"
cp -r "$TMP/claude-ads/.claude-plugin" "$DST/"
cp -r "$TMP/claude-ads/ads" "$DST/"
cp -r "$TMP/claude-ads/agents" "$DST/"
cp -r "$TMP/claude-ads/skills" "$DST/"
cp -r "$TMP/claude-ads/scripts" "$DST/"
cp "$TMP/claude-ads/LICENSE" "$DST/"
cp "$TMP/claude-ads/CLAUDE.md" "$DST/UPSTREAM-CLAUDE.md"
cp "$TMP/claude-ads/README.md" "$DST/UPSTREAM-README.md"

# Refresh NOTICE.md with the new commit info
cat > "$DST/NOTICE.md" <<EOF
# Attribution — claude-ads

This directory is a **vendored copy** of the open-source plugin **claude-ads** by AgriciDaniel, distributed under the MIT license. It is included inside the Mad-Minds marketplace so OnlineMinds marketers get its capabilities by installing the single marketplace.

- **Upstream repo:** $UPSTREAM
- **Upstream commit vendored:** \`$COMMIT\` ($DATE)
- **Upstream version:** $UPSTREAM_VERSION
- **License:** MIT — see \`LICENSE\` in this directory.

Run \`scripts/sync-claude-ads.sh\` from the Mad-Minds repo root to refresh.

## Boundary with onlineminds-marketing
This plugin is **analysis-only**. All write actions (pause campaigns, change budgets, edit GTM, etc.) go through the \`/ad-actions\` skill in the **onlineminds-marketing** plugin, which enforces the Tier 1 / Tier 2 spend-gate (verbatim typed accept-phrase for spend increases). Do not use claude-ads outputs to bypass that gate; surface findings, then apply through \`/ad-actions\`.
EOF

rm -rf "$TMP"

echo
echo "Done. Review the diff:"
echo "  git status"
echo "  git diff --stat"
echo
echo "If happy, bump the version in .claude-plugin/marketplace.json for the claude-ads entry to $UPSTREAM_VERSION, then commit:"
echo "  git add ."
echo "  git commit -m 'Sync claude-ads to upstream v$UPSTREAM_VERSION ($COMMIT)'"
echo "  git push"
