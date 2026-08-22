from __future__ import annotations

EXPLOITATION_START=20
FINAL_START=60


def validate_transition(before:dict,after:dict):
    bp=before['phase']; ap=after['phase']; bg=int(before['generation']); ag=int(after['generation'])
    if bp=='bootstrap':
        if ap!='exploration' or ag!=0: raise ValueError(f'bootstrap transition invalid: {bp}/{bg} -> {ap}/{ag}')
    elif bp in ('exploration','exploitation'):
        if ag!=bg+1: raise ValueError(f'generation did not increment exactly once: {bg}->{ag}')
        expected='final' if ag>=FINAL_START else ('exploitation' if ag>=EXPLOITATION_START else 'exploration')
        if ap!=expected: raise ValueError(f'phase after generation {ag} must be {expected}, got {ap}')
    elif bp=='final':
        if ap!='done' or ag!=bg: raise ValueError(f'final transition invalid: {ap}/{ag}')
    elif bp in ('done','stopped'):
        if ap!=bp or ag!=bg: raise ValueError('terminal state changed unexpectedly')
    else: raise ValueError(f'unknown phase {bp}')
    return True
