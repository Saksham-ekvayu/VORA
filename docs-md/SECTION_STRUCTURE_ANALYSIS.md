# Framework Extraction Section Structure Analysis

## Problem
The user reports that framework extraction was broken after changes to the section structure logic in `convert_to_section_structure()`.

## Git History
- **Original Version**: Commit `5e90814` - "feat: add extraction runner service for async document processing and control extraction"
- **Current Version**: Latest commit with hierarchical support for sub-controls
- **Breaking Changes**: Introduction of hierarchical logic that may skip controls

## Original Section Structure (Commit 5e90814)

### Key Characteristics:
1. **Simple, flat mapping** - controls are directly added to their sections
2. **Section determination** - by ID prefix matching:
   - For ID `A.6.1` → section is `A.6` (two-part prefix)
   - For ID `A` → section is `A`
3. **Priority order**:
   - Use `Section_name` if provided
   - Else use ID prefix (`A.6`, `A`, etc.)
   - Else use "NO_SECTION"
4. **All controls added** - every control goes directly into its section's `controls` array
5. **No hierarchy** - no parent-child relationships between controls

### Original Code Structure:
```python
def convert_to_section_structure(controls: list, resource_type: str = "framework") -> list:
    sections_map = {}
    section_order = []
    
    for idx, ctrl in enumerate(controls):
        # Extract control ID, name, description
        # Determine section by:
        # 1. Section_name (if provided)
        # 2. ID prefix (A.6 from A.6.1)
        # 3. NO_SECTION
        
        # Create section if new
        if sec_key not in sections_map:
            sections_map[sec_key] = {
                "id": sec_id,
                "name": sec_display_name,
                "controls": []  # All controls go here directly
            }
        
        # Create control object and ADD IT to section.controls
        control_obj = {
            "id": ctrl_id,
            "name": ctrl_name,
            "description": ctrl_desc,
            "deployment_points": dp_list,
        }
        sections_map[sec_key]["controls"].append(control_obj)  # DIRECT ADD
    
    return [sections_map[k] for k in section_order]
```

## Current Section Structure (With Hierarchical Support)

### Key Characteristics:
1. **Two-phase processing**:
   - Phase 1: Extract and organize controls into sections
   - Phase 2: Build hierarchy with parent-child relationships
2. **Hierarchy detection**:
   - 2-part ID (A.5) → Section header
   - 3-part ID (A.5.1) → Control (root in section A.5)
   - 4+ part ID (A.5.1.1) → Sub-control of A.5.1
3. **Conditional addition**:
   - Controls with 4+ parts are SKIPPED in Phase 2 if their parent exists
   - Controls are only added once (either as root or skipped if they have a parent)
4. **Structure with nesting**:
   - Sections contain root controls
   - Root controls can have "controls" array for sub-controls

### Current Code Logic (Simplified):
```python
def convert_to_section_structure(controls: list, resource_type: str = "framework") -> list:
    # Phase 1: Extract all controls
    for idx, ctrl in enumerate(controls):
        # Store control by ID
        control_by_id[ctrl_id] = ctrl_obj
        # Create section if needed
    
    # Phase 2: Organize controls into sections with hierarchy
    for ctrl_id, ctrl_obj in control_by_id.items():
        parts = _parse_id(ctrl_id)
        
        if len(parts) >= 4:
            # This is a sub-control (4+ parts like A.5.1.1)
            parent_id = ".".join(parts[:-1])  # Parent = A.5.1
            if parent_id in control_by_id:
                # Parent exists, SKIP THIS CONTROL - add as sub-control to parent
                continue  # ← PROBLEM: Control not added to section!
            else:
                # No parent, treat as root
                sec_key = ".".join(parts[:2]).upper()
        
        elif len(parts) == 3:
            # Control (3 parts like A.5.1)
            sec_key = ".".join(parts[:2]).upper()
        
        # Add to section.controls
        sections[sec_key]["controls"].append(ctrl_entry)
```

## The Breaking Change

### Problem: Controls Being Skipped
In the current implementation, when a control has a parent (4+ part ID), it's added to the parent's "controls" array but **NOT** added to the section's controls array.

This creates a **nested structure** where:
- Section contains root controls
- Root controls contain sub-controls

But in the **original flat format**, ALL controls appeared at the same level in their section.

### Example:

**Original Format (Working)**:
```json
{
  "id": "A.5",
  "name": "Access Control",
  "controls": [
    {"id": "A.5.1", "name": "User Access", ...},
    {"id": "A.5.1.1", "name": "Login Requirement", ...},  ← At section level
    {"id": "A.5.2", "name": "Admin Access", ...},
    {"id": "A.5.2.1", "name": "Privileged Access", ...}   ← At section level
  ]
}
```

**Current Format (Breaking)**:
```json
{
  "id": "A.5",
  "name": "Access Control",
  "controls": [
    {
      "id": "A.5.1",
      "name": "User Access",
      "controls": [  ← Nested sub-controls
        {"id": "A.5.1.1", "name": "Login Requirement", ...}
      ]
    },
    {
      "id": "A.5.2",
      "name": "Admin Access",
      "controls": [
        {"id": "A.5.2.1", "name": "Privileged Access", ...}
      ]
    }
  ]
}
```

## Where the Breaking Change Happens

### File: `backend/services/extract-controls-service/app/services/control_extractor.py`

**Lines 301-308** (Current problematic code):
```python
if len(parts) >= 4:
    # This is a sub-control (4+ parts like A.5.1.1)
    parent_id = ".".join(parts[:-1])  # Parent = A.5.1
    if parent_id in control_by_id:
        # Parent exists, treat as sub-control
        added_as_sub += 1
        logger.info(f"[STRUCTURE] {ctrl_id} → sub-control of {parent_id}")
        continue  ← THIS CONTINUE SKIPS ADDING TO SECTION!
```

The `continue` statement on line 308 means sub-controls are never added directly to sections.

**Lines 330-350** (Where they are supposed to be added as roots):
```python
# This is a root control - add it to the section
ctrl_entry = {...}

# Check if this control has sub-controls
sub_controls = []
for other_id in control_by_id:
    other_parts = _parse_id(other_id)
    if len(other_parts) >= 4:
        parent_id = ".".join(other_parts[:-1])
        if parent_id == ctrl_id:
            sub_obj = control_by_id[other_id]
            sub_controls.append({...})  ← They get added here as nested

if sub_controls:
    ctrl_entry["controls"] = sub_controls
```

## Impact on Framework Extraction

1. **Data Structure Changed** - Existing code expecting flat control arrays will break
2. **Queries/Filters** - Code that searches for controls by section will miss nested ones
3. **Comparison Logic** - Gap analysis comparing controls may not find nested sub-controls
4. **Merge Logic** - Historical merges may have used different structure

## Recommended Fix

### Option 1: Revert to Flat Structure (Safest)
Use the original `convert_to_section_structure` from commit `5e90814`:
- Maintains backward compatibility
- All controls at section level
- Original logic simple and proven

### Option 2: Keep Hierarchy but Fix Consumers
- Keep the new hierarchical structure
- Update all code that reads/processes controls to handle nested arrays
- Update gap analysis, comparison, merge logic
- Update database models to support nested controls

### Option 3: Provide Both
- Add a `flatten=True` parameter to `convert_to_section_structure`
- Return flat structure by default for compatibility
- Allow opt-in to hierarchical structure for new features

## Files to Review

1. **control_extractor.py** - Section structure conversion logic
2. **extraction_runner.py** - Uses `convert_to_section_structure`
3. **control_merger.py** - Merges controls (may expect flat structure)
4. **gap_runner.py** - Gap analysis (may search for controls incorrectly)
5. **Framework/DeploymentFramework models** - May have schema expectations

## Summary

The framework extraction was broken because the section structure changed from **flat** (all controls in section.controls) to **hierarchical** (nested sub-controls). Code that expects controls at the section level can no longer find them, causing extraction failures or incomplete data.

**Quick Fix**: Revert `convert_to_section_structure` to the original implementation from commit `5e90814`.
