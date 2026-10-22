# Claude Code prompts per member

How to use: `git pull`, create the branch named in the prompt, open Claude Code in the repo root, paste the prompt for
today. Claude reads CLAUDE.md automatically. Review the diff yourself, then push and open a PR. One prompt = one PR.
If Claude wants to change something outside your area or in `memledger/core/{types,interfaces}.py`, stop and ask M1.

Common footer (already included in every prompt): tests first, `make test` + `make lint` pass, stay in my folders,
no secrets/weights/datasets in git, small commits, then push the branch.
