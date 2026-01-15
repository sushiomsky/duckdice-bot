# Pull Request Template

## Description
<!-- Briefly describe the changes in this PR -->

## Type of Change
<!-- Mark with [x] the type of change -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Tests
- [ ] Build/deployment changes

## Related Issues
<!-- Link to related issues, e.g., "Fixes #123" or "Relates to #456" -->

## Testing Done
<!-- Describe the tests you ran to verify your changes -->

- [ ] All existing tests pass (`cd tests/gui && python3 test_gui_components.py`)
- [ ] Tested in simulation mode
- [ ] Tested with live API (if applicable)
- [ ] Manual testing performed
- [ ] New tests added (if applicable)

## Checklist

### Safety ✅
- [ ] No auto-start behavior introduced
- [ ] Stop button remains functional
- [ ] All user inputs are validated
- [ ] Error messages are clear and helpful
- [ ] No silent failures

### Code Quality ✅
- [ ] Code follows existing style and patterns
- [ ] Comments added for complex logic
- [ ] No TODOs left in code
- [ ] Functions are small and focused
- [ ] Proper error handling implemented

### UI/UX (if applicable) ✅
- [ ] UI remains responsive
- [ ] Changes work on different screen sizes
- [ ] Loading states/spinners used for long operations
- [ ] User feedback provided for all actions
- [ ] Follows color coding standards (green/red/yellow/gray)

### Database (if applicable) ✅
- [ ] Schema changes are backward compatible OR migration provided
- [ ] Database backup recommended in notes
- [ ] All queries are safe and efficient
- [ ] Proper indexing for new fields

### Documentation ✅
- [ ] User-facing changes documented in USER_GUIDE.md
- [ ] Technical changes documented in IMPLEMENTATION_COMPLETE.md
- [ ] Code comments updated
- [ ] CHANGELOG.md updated (if applicable)

## Screenshots
<!-- If UI changes, add before/after screenshots -->

## Performance Impact
<!-- Describe any performance implications -->

- [ ] No noticeable performance impact
- [ ] Performance improved
- [ ] Performance degraded (explain why it's acceptable)

## Breaking Changes
<!-- List any breaking changes and migration steps -->

None / [List breaking changes here]

## Additional Notes
<!-- Any other context, concerns, or discussion points -->

---

## Reviewer Notes

Please verify:
1. Safety standards maintained
2. Code quality meets project standards
3. Tests pass and coverage adequate
4. Documentation updated
5. No regression in existing features
