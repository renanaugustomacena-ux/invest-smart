# Skill: Git Advanced Workflows

You are an expert in advanced Git operations including history editing, selective commit application, binary search debugging, multi-branch development, and recovery techniques.

---

## When This Skill Applies

Activate this skill whenever:
- Cleaning up commit history before merging or creating a PR
- Applying specific commits across branches (cherry-pick)
- Finding the commit that introduced a bug (bisect)
- Working on multiple features simultaneously (worktrees)
- Recovering from Git mistakes or lost commits (reflog)
- Managing complex branch workflows
- Preparing clean PRs for review
- Synchronizing diverged branches

---

## 1. Interactive Rebase

The primary tool for editing Git history.

### Operations

| Command | Effect |
|---------|--------|
| `pick` | Keep commit as-is |
| `reword` | Change commit message only |
| `edit` | Pause to amend commit content |
| `squash` | Combine with previous commit, keep both messages |
| `fixup` | Combine with previous commit, discard this message |
| `drop` | Remove commit entirely |

### Usage

```bash
# Rebase last N commits
git rebase -i HEAD~5

# Rebase all commits on current branch since diverging from main
git rebase -i $(git merge-base HEAD main)
```

### Autosquash Workflow
```bash
# Make initial commit
git commit -m "feat: add user authentication"

# Later, fix something related to that commit
git commit --fixup abc123

# Rebase with autosquash (automatically marks fixup commits)
git rebase -i --autosquash main
```

### Split a Commit Into Multiple
```bash
# Interactive rebase, mark the commit with 'edit'
git rebase -i HEAD~3

# Git stops at that commit — undo it but keep the changes
git reset HEAD^

# Stage and commit in logical chunks
git add file1.py && git commit -m "feat: add validation"
git add file2.py && git commit -m "feat: add error handling"

# Continue rebase
git rebase --continue
```

---

## 2. Cherry-Picking

Apply specific commits from one branch to another without merging.

```bash
# Single commit
git cherry-pick abc123

# Range of commits (exclusive start)
git cherry-pick abc123..def456

# Stage changes only, do not commit
git cherry-pick -n abc123

# Cherry-pick and edit the message
git cherry-pick -e abc123

# Partial cherry-pick (specific files only)
git checkout abc123 -- path/to/file1.py path/to/file2.py
git commit -m "cherry-pick: apply specific changes from abc123"
```

### Conflict Handling
```bash
# If conflicts occur, resolve them, then:
git cherry-pick --continue

# Or abort entirely:
git cherry-pick --abort
```

---

## 3. Git Bisect

Binary search through commit history to find the exact commit that introduced a bug.

### Manual Bisect
```bash
git bisect start
git bisect bad HEAD          # Current commit is broken
git bisect good v1.0.0       # This commit was working

# Git checks out the midpoint — test it, then:
git bisect good   # if the bug is NOT present
git bisect bad    # if the bug IS present

# Repeat until Git identifies the offending commit
git bisect reset  # Clean up when done
```

### Automated Bisect
```bash
# Fully automated — script must exit 0 (good) or 1-127 (bad, except 125=skip)
git bisect start HEAD v1.0.0
git bisect run ./test.sh
```

**Rule:** Never bisect on a dirty working directory. Commit or stash first.

---

## 4. Worktrees

Work on multiple branches simultaneously in separate directories without stashing or switching.

```bash
# List existing worktrees
git worktree list

# Add worktree for an existing branch
git worktree add ../project-feature feature/new-feature

# Add worktree and create a new branch from main
git worktree add -b bugfix/urgent ../project-hotfix main

# Remove worktree when done
git worktree remove ../project-feature

# Prune stale worktree references
git worktree prune
```

**Rule:** Always clean up worktrees when done. Orphaned worktrees consume disk space.

---

## 5. Reflog — The Safety Net

Tracks all ref movements for 90 days, including deleted commits and branches.

```bash
# View full reflog
git reflog

# View reflog for specific branch
git reflog show feature/branch

# Recover a deleted commit
git reflog                        # Find the commit hash
git checkout abc123               # Inspect it
git branch recovered-branch abc123  # Create branch from it

# Recover a deleted branch
git reflog                        # Find last commit of deleted branch
git branch deleted-branch abc123  # Recreate it
```

---

## Practical Workflows

### Workflow 1: Clean Up Feature Branch Before PR
```bash
git checkout feature/user-auth
git rebase -i main
# Squash "fix typo" commits, reword messages, reorder logically, drop noise
git push --force-with-lease origin feature/user-auth
```

### Workflow 2: Apply Hotfix to Multiple Release Branches
```bash
git checkout main
git commit -m "fix: critical security patch"

git checkout release/2.0 && git cherry-pick abc123
git checkout release/1.9 && git cherry-pick abc123
```

### Workflow 3: Find Bug Introduction with Bisect
```bash
git bisect start HEAD v2.1.0
git bisect run npm test
# Git reports the exact commit that broke the tests
```

### Workflow 4: Multi-Branch Development with Worktrees
```bash
# Main work continues in ~/projects/myapp
git worktree add ../myapp-hotfix hotfix/critical-bug

cd ../myapp-hotfix
git commit -m "fix: resolve critical bug"
git push origin hotfix/critical-bug

cd ~/projects/myapp
git worktree remove ../myapp-hotfix
```

### Workflow 5: Recover from Accidental Reset
```bash
git reset --hard HEAD~5   # Mistake!

git reflog                # Find the lost commit hash
git reset --hard def456   # Restore to where you were
```

---

## Rebase vs. Merge Decision

| Use Rebase When | Use Merge When |
|----------------|---------------|
| Cleaning up local commits before push | Integrating completed features into main |
| Keeping feature branch current with main | Preserving exact collaboration history |
| Creating linear history for easier review | Working on public/shared branches |

### Update Feature Branch with Main (Rebase)
```bash
git checkout feature/my-feature
git fetch origin
git rebase origin/main
# Resolve conflicts if any, then:
git add . && git rebase --continue
```

---

## Safety Rules — Non-Negotiable

1. **Always use `--force-with-lease`** instead of `--force`. It prevents overwriting others' work.
2. **Never rebase commits that have been pushed and shared** with other developers.
3. **Create a backup branch before risky operations:**
   ```bash
   git branch backup-branch
   git rebase -i main
   # If something goes wrong:
   git reset --hard backup-branch
   ```
4. **Test after every history rewrite** before force pushing.
5. **Keep commits atomic** — each commit is a single logical change.
6. **Commit or stash before bisecting** — never bisect on a dirty working directory.

---

## Recovery Commands — Quick Reference

```bash
# Abort operations in progress
git rebase --abort
git merge --abort
git cherry-pick --abort
git bisect reset

# Restore file from specific commit
git restore --source=abc123 path/to/file

# Undo last commit, keep changes staged
git reset --soft HEAD^

# Undo last commit, discard changes
git reset --hard HEAD^

# Recover deleted branch (within 90 days)
git reflog
git branch recovered-branch abc123
```

---

## Checklist Before Force Pushing

- [ ] I have backed up the branch or can recover via reflog
- [ ] I am using `--force-with-lease`, not `--force`
- [ ] No one else is working on this branch
- [ ] I have tested the rewritten history (builds, tests pass)
- [ ] Commit messages are clean, descriptive, and atomic
