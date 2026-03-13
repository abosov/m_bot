# Review Checklist

## Functional checks
- Script creates `automation/bundles/active/<STORY_ID>/`
- Script creates all 7 required bundle files
- Script fills `STORY_ID` and `STORY_TITLE` where appropriate
- Script fails if bundle already exists
- Script validates input format

## Safety checks
- No overwrite of existing files
- No unrelated repository changes
- No changes outside allowed scope

## Quality checks
- Generated files are readable and easy to edit
- Templates are reused where practical
- Output and error messages are understandable
