#!/bin/bash
#
# Create a Release
# Tags the release and triggers build pipeline
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Get version
if [ -z "$1" ]; then
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 2.0.0"
    exit 1
fi

VERSION=$1
TAG="v$VERSION"

echo "🚀 Creating Release v$VERSION"
echo "=========================================="
echo ""

# Check if tag exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "❌ Error: Tag $TAG already exists"
    exit 1
fi

# Check git status
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update version in pyproject.toml
echo "Updating version in pyproject.toml..."
if [ -f "pyproject.toml" ]; then
    sed -i.bak "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    rm -f pyproject.toml.bak
    git add pyproject.toml
fi

# Create CHANGELOG entry
echo ""
echo "Creating CHANGELOG entry..."
DATE=$(date +"%Y-%m-%d")

if [ ! -f "CHANGELOG.md" ]; then
    cat > CHANGELOG.md << EOF
# Changelog

All notable changes to this project will be documented in this file.

## [$VERSION] - $DATE

### Added
- Modern GUI with persistent settings
- Target-Aware strategy with dedicated UI
- Simulation mode for risk-free testing
- Multi-currency balance management
- Automated release pipeline

### Changed
- Complete GUI refactor with Material Design
- Enhanced UX with keyboard shortcuts

### Fixed
- Various bug fixes and improvements

EOF
else
    # Prepend to existing changelog
    TEMP=$(mktemp)
    echo "## [$VERSION] - $DATE" > "$TEMP"
    echo "" >> "$TEMP"
    echo "### Added" >> "$TEMP"
    echo "- Release v$VERSION" >> "$TEMP"
    echo "" >> "$TEMP"
    cat CHANGELOG.md >> "$TEMP"
    mv "$TEMP" CHANGELOG.md
fi

git add CHANGELOG.md

# Commit version bump
echo ""
echo "Committing version bump..."
git commit -m "chore: bump version to $VERSION" || true

# Create tag
echo ""
echo "Creating git tag: $TAG..."
git tag -a "$TAG" -m "Release $VERSION"

# Build locally
echo ""
read -p "Build locally before pushing? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Building..."
    export VERSION=$VERSION
    bash scripts/build.sh
fi

# Push
echo ""
read -p "Push tag to remote? This will trigger CI build. (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Pushing to remote..."
    git push origin main
    git push origin "$TAG"
    
    echo ""
    echo "✅ Release $VERSION created and pushed!"
    echo ""
    echo "GitHub Actions will now build releases for all platforms."
    echo "Check: https://github.com/YOUR_USERNAME/duckdice-bot/actions"
    echo ""
else
    echo ""
    echo "Tag created locally but not pushed."
    echo "To push later:"
    echo "  git push origin main"
    echo "  git push origin $TAG"
    echo ""
fi

