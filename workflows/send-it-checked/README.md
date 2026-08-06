# send-it-checked — spec to PR, unattended, with review and QA

[`send-it`](../send-it/) with a staff review and a QA pass inserted before the
ship step. Still unattended end to end; still ends in an open pull request.

```bash
specify workflow run send-it-checked -i spec="add dark mode" -i target_branch=main
```

## Requires

| Extension | Why |
|---|---|
| [`ship`](https://github.com/arunt14/spec-kit-ship) | The `ship` step dispatches `speckit.ship.run` |
| [`staff-review`](https://github.com/arunt14/spec-kit-staff-review) | The `review` step dispatches `speckit.staff-review.run` |
| [`qa`](https://github.com/arunt14/spec-kit-qa) | The `qa` step dispatches `speckit.qa.run` |
| [`screenshots`](https://github.com/clintcparker/speckit-addons/tree/main/extensions/screenshots) | The two capture steps dispatch `speckit.screenshots.capture` |

All four are hard dependencies: a missing extension means the step fails at
dispatch. Spec Kit's workflow schema cannot declare this — `requires` accepts
only `speckit_version` and `integrations` — so install them first:

```bash
specify extension catalog add \
  https://raw.githubusercontent.com/clintcparker/speckit-addons/main/extensions/catalog.json \
  --name speckit-addons --install-allowed --priority 5
specify extension add ship
specify extension add staff-review
specify extension add qa
specify extension add screenshots
```

The worktree-first flow this workflow assumes additionally wants the `worktrees`
and `git` extensions — see [docs/send-it-harness.md](../../docs/send-it-harness.md).

## Why this exists

`send-it` skips review and QA. That is not a waiver — ship's pre-flight review
and QA checks are gated on `FEATURE_DIR/reviews/` and `FEATURE_DIR/qa/`
existing, and in a `send-it` run they never do, so pre-flight passes honestly
with nothing to check.

`send-it-checked` makes those directories exist. `speckit.staff-review.run`
writes to `reviews/` and `speckit.qa.run` writes to `qa/`, so ship's pre-flight
gates are real: it reads the most recent report of each and reacts to the
verdict.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `spec` | yes | — | What you want built. Passed to `specify`, `plan`, `tasks`, and `implement`. |
| `integration` | no | `auto` | Which agent integration to dispatch to. `auto` uses whatever the project was initialized with. |
| `target_branch` | no | `main` | The branch the pull request targets. |

## Steps

```mermaid
flowchart TB
    A["specify<br/>(command)"] --> B["plan<br/>(command)"]
    B --> C["tasks<br/>(command)"]
    C --> D["screenshots-before<br/>(command)"]
    D --> E["implement<br/>(command)"]
    E --> F["review<br/>(command)"]
    F --> G["qa<br/>(command)"]
    G --> H["screenshots-after<br/>(command)"]
    H --> I["ship<br/>(command)"]

    style A fill:#49a,color:#fff
    style B fill:#49a,color:#fff
    style C fill:#49a,color:#fff
    style D fill:#49a,color:#fff
    style E fill:#49a,color:#fff
    style F fill:#6a5,color:#fff
    style G fill:#6a5,color:#fff
    style H fill:#49a,color:#fff
    style I fill:#a63,color:#fff
```

| Step | Command | Provided by |
|---|---|---|
| `specify` | `speckit.specify` | core |
| `plan` | `speckit.plan` | core |
| `tasks` | `speckit.tasks` | core |
| `screenshots-before` | `speckit.screenshots.capture` | `screenshots` extension |
| `implement` | `speckit.implement` | core |
| `review` | `speckit.staff-review.run` | `staff-review` extension |
| `qa` | `speckit.qa.run` | `qa` extension |
| `screenshots-after` | `speckit.screenshots.capture` | `screenshots` extension |
| `ship` | `speckit.ship.run` | `ship` extension |

Note that `/speckit.review` and `/speckit.qa`, which ship's own README
name-drops, do not exist as core commands. `speckit.staff-review.run` and
`speckit.qa.run` are the real ones.

## The remediation policy

Both checks get exactly one fix-and-re-run pass:

- **Review:** on CHANGES REQUIRED, fix every Blocker finding, re-run the review
  once, then move on whatever the second verdict says.
- **QA:** on FAILURES FOUND, fix the failing scenarios, re-run QA once, then
  move on whatever the second verdict says.

Anything still outstanding after that pass does **not** stop the ship. It goes
into the pull request description under a "Known issues" heading. The pull
request stays the gate — the checks exist to make it a better-informed one, not
to block an unattended run indefinitely.

## Caveats

- **Everything in [`send-it`'s caveats](../send-it/README.md#caveats) applies.**
- **Verdict handling is agent-interpreted.** Ship reads the review and QA
  reports and reasons about the verdict; there is no machine-readable status
  field. The reports are markdown and the emoji upstream uses for a
  "changes required" verdict is not identical across the two extensions.
- **QA mode selection is a heuristic.** The step asks for CLI QA unless browser
  automation is clearly already configured. On a web project without Playwright
  installed you get CLI QA, which is shallower than browser QA would be.
- **Two extra full agent passes.** This is meaningfully slower and more
  expensive than `send-it`. Use `send-it` when you already trust the change.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
