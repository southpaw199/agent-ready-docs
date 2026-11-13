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

### Seven tokens to get the permissions right

The reviewer's scripts use a fine-grained GitLab token, and it took seven versions of it, over two days, to cover what they needed. Each gap showed up only when a script happened to make the call that needed it, and fine-grained tokens can't be edited, so every gap meant a new token. The gaps had several causes:

- **Permissions sat under unexpected resources.** Reading files needs Repository: Read, which searching the form for "file" doesn't find. Merging needs Merge Request: Merge, separate from Update. Protecting a branch needs Branch: Protect, although the Protected Branch resource is where you'd look, and it offers only Read and Update.
- **One permission went in at the wrong level.** Creating projects is a user-level permission, and it was added under the group, where it does nothing.
- **Re-entering a dozen permissions by hand dropped some.** Branch: Read went missing on one token, Repository: Read on another.

GitLab deserves credit here: every refusal named the exact missing permission, so each fix took one step once it was found.

**Takeaway:** when an agent helps you set up credentials, have it also write a check that exercises every read permission the work needs, and run it right after creating each token. Ours, `check_token.py`, makes one harmless request per permission and names any that are refused. Write permissions can't be checked without changing something, so list them and check them by eye, or test them early with a throwaway project rather than halfway through real work.

### "The new token" meant a different token to each of us

At one point there were two tokens: the reviewer's, for the setup scripts, and a smaller one for a single project. The reviewer created a replacement for the project token. The agent assumed it was the reviewer's token, and spent several rounds of checks puzzling over why "the new token" still lacked a permission. Each check passed, but only because it was testing the old reviewer token, which hadn't been replaced at all.

**Takeaway:** when there's more than one credential, name each one every time, in instructions and in questions, and keep each in its own clearly named file. An agent that hears "I created the new token" should ask which one before building on the answer.

### A deliberately wrong answer found a gap in the checker

Each task's checker was first run against a correct reference solution, and passed it. For two tasks, a control run followed: a configuration with the exact mistake the task is designed to catch. For G2, a duplicate-pipeline trap, the checker failed it as intended. For G3, a stage that isn't listed, the checker passed the criterion meant to catch it. GitLab rejects that configuration, but leaves the pipeline's `yaml_errors` field empty, and the checker relied on that field. The fix was to require at least one job as well, and the control now fails as it should.

**Takeaway:** a checker that passes a good answer has shown only half of what it must. Run at least one known-bad answer through it, ideally the mistake the task is about, before trusting it to score anyone else's work.

### Evidence was nearly changed twice by tools meant to help

Saved job logs are evidence and must stay exactly as GitLab returned them. Twice, they nearly didn't. Once, the logs were saved while a check was still running, so one log was cut off mid-job. Another time, the pre-commit hooks reformatted a set of logs saved one folder deeper than the exclude pattern covered. They were restored from the staged copies.

**Takeaway:** don't rely on instructions about order or folder layout to protect evidence. Make the tools notice themselves: the log saver now refuses to report success while a job is still running. And when you add a new place for evidence, run the hooks over everything once and check that nothing changed.

### Seeding at scale meets rate limits

Seeding a project with 105 merge requests, each with its own commit, got through about 70 before GitLab.com answered 429 Too Many Requests. Earlier, a missing permission had stopped the same seed after two.

**Takeaway:** scripts that create test data in bulk should be able to resume, skipping what already exists, and should wait and retry on rate limits instead of failing. Otherwise every interruption means starting over, and usually means another project or credential to clean up.
