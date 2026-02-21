# OpenNode — Task System

## Overview

This directory contains all implementation tasks for the OpenNode project. Each task is a self-contained Markdown file describing what needs to be built, with steps, code references, and acceptance criteria.

Tasks are designed to be executed by **Claude Code agents** — either one at a time or in parallel by multiple agents.

## Directory Structure

```
tasks/
├── README.md          ← You are here
├── backlog/           ← Tasks waiting to be picked up
├── in-progress/       ← Tasks currently being worked on by an agent
└── done/              ← Completed tasks
```

## How It Works

### Picking up a task

1. Look in `backlog/` for available tasks
2. Choose the **lowest-numbered task** whose dependencies are met (see dependency map below)
3. **Move the file** from `backlog/` to `in-progress/` before starting work
4. This signals to other agents that the task is taken — avoids duplicate work

### Completing a task

1. Verify all acceptance criteria listed at the bottom of the task file
2. **Move the file** from `in-progress/` to `done/`
3. Check `backlog/` for the next available task

### If a task is blocked

If you can't complete a task (missing dependency, unclear requirement, etc.):
1. Add a `## Blocked` section at the top of the task file explaining why
2. Move it **back to `backlog/`**
3. Pick a different task that isn't blocked

## Dependency Map

Tasks should be executed respecting these dependencies. Tasks at the same level CAN run in parallel.

```
Level 0 (no dependencies):
  00-project-setup

Level 1 (depends on 00):
  01-python-backend-core
  05-electron-shell

Level 2 (depends on 01):
  02-asr-engine
  03-vad-pipeline
  12-export-and-storage

Level 3 (depends on 02 + 03):
  04-websocket-server

Level 4 (depends on 04 + 05):
  06-audio-capture
  09-electron-python-integration

Level 5 (depends on 06 + 09):
  07-overlay-window
  08-main-window-ui
  14-system-tray

Level 6 (depends on 04):
  10-speaker-diarization
  11-meeting-summarization

Level 7 (depends on 05):
  13-settings-and-config

Level 8 (depends on all previous):
  15-packaging-and-distribution
  16-testing-and-qa
```

### Parallel execution example

Two agents working simultaneously:
- **Agent A**: picks `01-python-backend-core` → moves to `in-progress/`
- **Agent B**: picks `05-electron-shell` → moves to `in-progress/`
- Both work independently, no conflicts.

## Task File Format

Each task file follows this structure:

```markdown
# Task NN: Title

## Objective
What this task achieves.

## Steps
### 1. Step name
Details, code snippets, file paths.

### 2. Another step
...

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

## Notes for Agents

- **Always read the full task file before starting.** Understand the scope.
- **Read `README.md` in the project root** for architecture context.
- **Check `in-progress/` and `done/`** before picking a task — respect dependencies.
- **Write tests** as part of the task when the task mentions them.
- **Commit after each completed task** with message format: `feat(opennode): complete task NN - <title>`
- If you need to create files not mentioned in the task, that's fine — use the project structure from the README as a guide.
