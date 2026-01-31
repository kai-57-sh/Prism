#!/bin/bash
# Update task status in tasks.md file

TASKS_FILE="/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/tasks.md"

# Check if tasks file exists
if [ ! -f "$TASKS_FILE" ]; then
    echo "Tasks file not found: $TASKS_FILE"
    exit 1
fi

# Update Phase 4 tasks as completed
sed -i 's/- \[ \] T074 \[US2\]/- [x] T074 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T075 \[US2\]/- [x] T075 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T076 \[US2\]/- [x] T076 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T077 \[US2\]/- [x] T077 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T078 \[US2\]/- [x] T078 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T079 \[US2\]/- [x] T079 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T080 \[US2\]/- [x] T080 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T081 \[US2\]/- [x] T081 [US2]/' "$TASKS_FILE"
sed -i 's/- \[ \] T082 \[US2\]/- [x] T082 [US2]/' "$TASKS_FILE"

echo "Phase 4 tasks marked as completed in $TASKS_FILE"
