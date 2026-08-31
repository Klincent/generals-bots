from __future__ import annotations

from . import orchestrator as b
from . import orchestrator_pool as p
from . import orchestrator_focus as f
from . import orchestrator_breeding as breeding
from . import orchestrator_cmaes as cma
from .orchestrator_behavior_safe import persist_resilient_v2


CMA_FULL_LAMBDA = 64


def create_challengers_cmaes_full(state: dict):
    generation = int(state['lineage_generation'])
    attempt = int(state['promotion_attempt']) + 1
    pool = breeding.ensure_breeding_pool(state)
    known = {path.name[:-5] for path in b.GENOMES.glob('*.json')}

    ids, created, info = cma.sample_candidates(
        state,
        pool,
        known,
        attempt,
        count=CMA_FULL_LAMBDA,
    )
    if len(ids) != CMA_FULL_LAMBDA:
        raise RuntimeError(f'CMA-ES population budget drifted: {len(ids)}')

    f.phase_heartbeat(
        state,
        'cmaes_full_population_created',
        challengers=len(ids),
        search_engine='cma_es_full',
        cma_es_generation=info['es_generation'],
        cma_es_sigma=info['sigma'],
        cma_es_anchor=info['anchor_gid'],
        cma_es_dimension=info['dimension'],
        cma_es_lambda=CMA_FULL_LAMBDA,
    )
    return ids, created, {'cma_es_full': len(ids)}


def main() -> None:
    # Keep Runtime v2 and the hardened transaction/persistence path, but devote
    # the entire 64-candidate population to CMA-ES covariance learning.
    b.persist = persist_resilient_v2
    f.persist_resilient = persist_resilient_v2
    b.opponent_mix = f.focus_opponent_mix
    p._phase_heartbeat = f.phase_heartbeat
    b.screen = p.screen_parallel
    b.create_challengers = create_challengers_cmaes_full
    b.deep_lineage = f.deep_lineage_focus
    b.transaction = breeding.transaction_breeding
    b.main()


if __name__ == '__main__':
    main()
