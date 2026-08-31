from __future__ import annotations

from pathlib import Path

from . import orchestrator as b
from . import orchestrator_focus as f
from . import orchestrator_behavior as behavior
from . import orchestrator_breeding as breeding


def persist_resilient_v2(paths: list[Path], message: str) -> None:
    """Persist safely when the durable control branch advances during a run.

    Generated/evaluator files can leave the runner worktree dirty.  The old
    recovery used a plain rebase, which aborts before rebasing when tracked
    files are unstaged.  --autostash makes that recovery transactional while
    preserving the generated worktree changes.
    """
    uniq: list[Path] = []
    for path in paths:
        if path.exists() and path not in uniq:
            uniq.append(path)
    if not uniq:
        return

    b.run_git('add', *[str(path) for path in uniq])
    if b.run_git('diff', '--cached', '--quiet', check=False).returncode == 0:
        return
    b.run_git('commit', '-m', message)

    for _ in range(6):
        push = b.run_git('push', 'origin', f'HEAD:{b.CONTROL}', check=False)
        if push.returncode == 0:
            return

        b.run_git('fetch', '--no-tags', 'origin', b.CONTROL)
        rebased = b.run_git('rebase', '--autostash', f'origin/{b.CONTROL}', check=False)
        if rebased.returncode != 0:
            b.run_git('rebase', '--abort', check=False)
            raise RuntimeError('lineage persist failed: autostash rebase conflicted')

    raise RuntimeError('lineage persist failed after six push/autostash-rebase attempts')


def main() -> None:
    # behavior.main() installs f.persist_resilient into the base orchestrator,
    # so replace that function before entering the behavior runtime.
    f.persist_resilient = persist_resilient_v2

    # Install cumulative evolution before behavior.main wires the runtime:
    # promising non-promoted challengers become future parents, and a few slots
    # perform a directional numerical line search from the strongest near-winners.
    breeding.install()
    behavior.main()


if __name__ == '__main__':
    main()
