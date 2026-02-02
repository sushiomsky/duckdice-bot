# PyPI Publishing Setup

## Current Status

The `build-and-release.yml` workflow supports **two methods** for PyPI publishing:

### Method 1: API Token (Current)
- Requires secret: `PYPI_API_TOKEN`
- Workflow uses `twine upload` with the token
- **Issue**: Secret may be invalid/expired

### Method 2: Trusted Publishing (Recommended)
- No secrets needed
- More secure (uses OIDC)
- Workflow already supports it (fallback)

## To Fix PyPI Publishing

### Option A: Update the API Token Secret

1. Go to PyPI: https://pypi.org/manage/account/token/
2. Generate a new API token for `duckdice-betbot`
3. Go to GitHub repo settings: https://github.com/sushiomsky/duckdice-bot/settings/secrets/actions
4. Update `PYPI_API_TOKEN` with the new token

### Option B: Switch to Trusted Publishing (Recommended)

1. **Remove the old secret**:
   - Go to: https://github.com/sushiomsky/duckdice-bot/settings/secrets/actions
   - Delete `PYPI_API_TOKEN`

2. **Configure PyPI trusted publisher**:
   - Go to: https://pypi.org/manage/project/duckdice-betbot/settings/publishing/
   - Add a new trusted publisher:
     - **Owner**: `sushiomsky`
     - **Repository**: `duckdice-bot`
     - **Workflow**: `build-and-release.yml`
     - **Environment** (optional): `pypi`

3. **That's it!** Next tag push will use trusted publishing automatically.

## How the Workflow Decides

```yaml
# Uses twine if secret exists
- name: Publish to PyPI (with token)
  if: ${{ secrets.PYPI_API_TOKEN }}
  env:
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
  run: twine upload dist/*

# Falls back to trusted publishing if no secret
- name: Publish to PyPI (trusted publishing)
  if: ${{ !secrets.PYPI_API_TOKEN }}
  uses: pypa/gh-action-pypi-publish@release/v1
```

## Testing

To test PyPI publishing without creating a real release:

```bash
# 1. Create a test tag locally
git tag v4.11.1-test
git push origin v4.11.1-test

# 2. Watch the workflow run
# 3. Delete the test tag if successful
git tag -d v4.11.1-test
git push origin :refs/tags/v4.11.1-test
```

## Current Workflow Status

- ✅ **ci.yml**: Basic tests - WORKING
- ✅ **build-and-release.yml**: Builds + PyPI - WORKING (tests passing)
- ❌ **PyPI publishing**: Only runs on tags (`refs/tags/v*`)
- ✅ **GitHub releases**: Only runs on tags

## Next Steps

1. Choose Option A or B above
2. Push a version tag to test:
   ```bash
   git tag v4.11.1
   git push origin v4.11.1
   ```
3. Verify PyPI upload succeeds
4. If using trusted publishing, no more secret management needed!
