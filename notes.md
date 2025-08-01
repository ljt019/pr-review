# Bug Bot Development Notes

## Textual TUI Lessons Learned

### Centering Text in Widgets

**Problem**: `text-align: center` doesn't work on some widgets like Labels by default.

**Solution**: Different widgets have different default widths:
- **OptionList options**: Already have some default width, so `text-align: center` works immediately
- **Labels**: Have auto width (only as wide as their text), so `text-align: center` has no effect

**Fix for Labels**: Set explicit width first, then center:
```css
Label {
    width: 100%;        /* Make label span full width */
    text-align: center; /* Now centering works */
}
```

### Widget CSS Organization

**Issue**: When extracting widgets to separate files, giving each widget its own `CSS_PATH` can break global styling like Screen centering.

**Solution**: Keep all CSS in the main app.tcss file and don't set individual `CSS_PATH` on widgets. This preserves global styling rules while keeping widget code modular.

### Screen Centering

**Working Pattern**:
```css
Screen {
    background: $background;
    align: center middle;
}
```

This centers content at the Screen level. Individual widget styling should not interfere with this unless absolutely necessary.

## General Development Notes

- When refactoring, always test that existing functionality still works
- CSS specificity matters - use scoped selectors like `ModelSelectScreen Label` to target specific screens
- Path management is much cleaner with a centralized paths module