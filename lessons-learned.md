# Lessons learned

Observations from running the case studies that aren't findings about the product's docs, but are worth knowing for anyone who works alongside an AI coding agent. Each one comes from something that actually went wrong, or nearly did, while setting up or running a case study.

## agent-ready-gitlab

Case study 3, on GitLab's CI/CD and REST API docs, is in progress. These notes come from setting up its test group, reviewer token, setup scripts and checkers, with Claude Code doing most of the scripting and the reviewer running every command that touched credentials or pushed code.

### The agent guided a web form it couldn't see

GitLab's fine-grained token form shows only some permission categories until you search for one. The reviewer pasted the first list they saw, and the agent took it as the complete list. The missing categories only turned up when the reviewer searched for "merge". The first token was also missing the Code: Download permission, which cloning needs. GitLab's tokens can't be edited after they're created, so it had to be replaced.

GitLab deserves credit here: the 403 error named the exact missing permission, so the fix took one step.

**Takeaway:** when an agent talks you through a UI, it's working from your description, not the screen. Tell it what you can't see as well as what you can, such as collapsed sections, search boxes and paginated lists. Expect it to assume a list is complete unless you say otherwise.

### A secret reached the agent through the editor

The new token was briefly selected in an untitled editor tab. The IDE integration sends the current selection to the agent along with the next message, so the token went to the model without being pasted into the chat. The agent flagged it, the token was rotated, and the agent never repeated it.

**Takeaway:** in an agent-enabled editor, a selection or open file counts as a message. Paste secrets only into a prompt that writes straight to a protected file, such as `( umask 077; cat > ~/.config/…/token )`, and never into an editor tab, even an unsaved one.

### The agent's shell and the reviewer's terminal are different places

A script failed with "Set REVIEW_GITLAB_TOKEN" because the token had been exported in a different terminal. That was by design: the token was kept out of the agent's shell and out of VS Code, and was exported only in a separate setup terminal. Having more than one terminal made it easy to run a command in the wrong one.

**Takeaway:** decide which terminal holds which credentials, and say so in every instruction the agent gives. Scripts should fail with a message naming the missing variable, not a traceback, so the mistake is obvious. Keeping the agent's shell credential-free is worth the extra friction.

### Repeated passphrase prompts weren't a wrong passphrase

Every `git push` asked for the SSH key's passphrase again and again. `ssh-keygen -y` showed that the passphrase was correct. The cause was Git LFS's pre-push hook, which checks for file locks over its own SSH connections and prompts once for each one. Fixed with `git config --local lfs.locksverify false`.

**Takeaway:** a symptom that looks like a user error may be a tool you didn't know was running. Verify the obvious cause in isolation before trying it again. A prompt the agent's shell can't answer, such as an SSH passphrase, also means that step has to be the reviewer's.

### Commands written for pasting need to survive pasting

A two-line `cp` command, joined with a trailing `\`, lost its second line when pasted into the terminal and failed. After that, the agent gave pasted commands as single lines.

**Takeaway:** when an agent hands you commands to run, prefer one command per line with no line continuations, or a script file. What reads well in the chat isn't always what reaches the shell.

### Generated commands need tests that run them

The agent wrote a helper that builds a `git clone` command with a one-off credential helper, so the token is never saved in the clone's config. It looked right, but git rejected it ("key does not contain a section"), because the second `-c` option was missing `credential.helper=`. The fix came with two tests: one that parses the command as the shell would, and one that runs real `git config` with the same options.

**Takeaway:** a command an agent builds as a string is code, and needs a test that executes it. Reading it isn't enough, for the agent or for the reviewer.

### Tests the agent wrote passed, and the checker still failed

The G1 checker reads GitLab job logs to confirm that pytest ran and that pip used the cache. Its tests passed on sample logs the agent had written. On the first real run it scored two checks as failures, although the pipelines had passed. GitLab.com starts every line of a job log with a timestamp and stream tag, which the sample logs didn't include. A second pattern matched the runner's helper image, not the job's image. Both were fixed, and the real logs are now part of the tests.

**Takeaway:** tests an agent writes for its own code share its assumptions. Check parsers against a real artifact as early as you can, and keep that artifact as a test fixture. This is the same rule the method applies to agents' runs: an agent saying it succeeded isn't evidence that it did.
