# Code Cleanup Recommendations

## Duplicate Functions to Remove:

### 1. vai_window_CTRL.py
- Remove: `open_app()` function (lines ~180-220)
- Remove: `close_app()` function (lines ~250-290)
- Keep: Only `folder_file()` function

### 2. vai_file_opner.py  
- Keep as is (used by enhanced_tools.py)
- But update agent.py to use `verified_play_file` instead

### 3. agent.py Tool List
Update imports to use only verified versions:
```python
# Remove these from tools list:
# open_app, close_app, Play_file

# Keep only:
verified_open_app, verified_close_app, verified_play_file
```

### 4. web_automation.py
- Keep simple functions for basic use
- RoboticAgent class for advanced automation
- No removal needed (different use cases)

## Files to Update:

1. **agent.py** - Update tool imports
2. **vai_window_CTRL.py** - Remove duplicate functions  
3. **enhanced_tools.py** - Keep as primary interface

## Benefits:
- Reduces code duplication by ~200 lines
- Ensures all actions use verification
- Prevents hallucination issues
- Cleaner codebase maintenance