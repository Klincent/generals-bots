"""Synthetic aggressive opponent used to stress concentrated-doomstack defence.

The policy intentionally resembles the observed failure mode: expand first, then
pull many 3+ stacks off the edges/rear through owned territory into one locked
rally stack, leaving one behind. Once the carrier is large enough it drives
through visible enemy territory; before contact it searches toward the opposite
side of the board. This is a stress opponent, not a general-purpose submission.
"""
from collections import deque
import sys

PASS = (1, 0, 0, 0, 0)
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def passable(t):
    return t not in (2, 5)


class Agent:
    def __init__(self, player_id, H, W):
        self.player_id = player_id
        self.H = H
        self.W = W
        self.rally = None
        self.attack = False
        self.own_general = None
        self.last_enemy_general = None

    def _owned(self, obs):
        return [(r, c) for r in range(obs.H) for c in range(obs.W)
                if obs.owner_grid[r][c] == 1]

    def _largest(self, obs):
        cells = self._owned(obs)
        return max(cells, key=lambda x: obs.army_grid[x[0]][x[1]], default=None)

    def _dir(self, a, b):
        dr, dc = b[0] - a[0], b[1] - a[1]
        for d, delta in enumerate(DIRS):
            if delta == (dr, dc):
                return d
        return 0

    def _owned_dist(self, obs, target):
        """BFS distances to target using only our connected territory."""
        dist = {target: 0}
        q = deque([target])
        while q:
            r, c = q.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                p = (nr, nc)
                if not (0 <= nr < obs.H and 0 <= nc < obs.W):
                    continue
                if p in dist or obs.owner_grid[nr][nc] != 1:
                    continue
                dist[p] = dist[(r, c)] + 1
                q.append(p)
        return dist

    def _path_step(self, obs, src, target):
        """First shortest-path step through all currently passable cells."""
        if src == target:
            return None
        q = deque([src])
        prev = {src: None}
        while q:
            cur = q.popleft()
            if cur == target:
                break
            r, c = cur
            # Mild deterministic target bias: consider neighbors reducing
            # Manhattan distance first, then fixed direction order.
            ns = []
            for d, (dr, dc) in enumerate(DIRS):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < obs.H and 0 <= nc < obs.W):
                    continue
                if not passable(obs.type_grid[nr][nc]):
                    continue
                p = (nr, nc)
                ns.append((abs(nr-target[0]) + abs(nc-target[1]), d, p))
            for _, _, p in sorted(ns):
                if p in prev:
                    continue
                prev[p] = cur
                q.append(p)
        if target not in prev:
            return None
        cur = target
        while prev[cur] != src:
            cur = prev[cur]
            if cur is None:
                return None
        return cur

    def _expand(self, obs):
        best = None
        best_score = -10**9
        for r, c in self._owned(obs):
            a = obs.army_grid[r][c]
            if a <= 1:
                continue
            for d, (dr, dc) in enumerate(DIRS):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < obs.H and 0 <= nc < obs.W):
                    continue
                if not passable(obs.type_grid[nr][nc]):
                    continue
                own = obs.owner_grid[nr][nc] == 1
                dest = obs.army_grid[nr][nc]
                if own:
                    continue
                if a <= dest + 1:
                    continue
                owner = obs.owner_grid[nr][nc]
                typ = obs.type_grid[nr][nc]
                # Strongly prefer enemy, then visible neutral, then fog. Use
                # larger source stacks so expansion itself creates feeder tails.
                score = a
                if owner == 2:
                    score += 10000
                elif typ not in (0, 5):
                    score += 3000
                else:
                    score += 1200
                if typ == 4:
                    score += 50000
                if score > best_score:
                    best_score = score
                    best = (0, r, c, d, 0)
        return best

    def _enemy_target(self, obs, carrier):
        enemy_general = None
        enemies = []
        for r in range(obs.H):
            for c in range(obs.W):
                if obs.owner_grid[r][c] == 2:
                    enemies.append((r, c))
                    if obs.type_grid[r][c] == 4:
                        enemy_general = (r, c)
        if enemy_general is not None:
            self.last_enemy_general = enemy_general
            return enemy_general
        if self.last_enemy_general is not None:
            return self.last_enemy_general
        if enemies:
            # Punch the closest visible frontier to establish/maintain contact.
            return min(enemies, key=lambda p: abs(p[0]-carrier[0]) + abs(p[1]-carrier[1]))

        # No contact: search the side farthest from our own general. General is
        # visible on our own board and gives a stable direction across the map.
        if self.own_general is None:
            for r, c in self._owned(obs):
                if obs.type_grid[r][c] == 4:
                    self.own_general = (r, c)
                    break
        g = self.own_general or carrier
        corners = [(0, 0), (0, obs.W-1), (obs.H-1, 0), (obs.H-1, obs.W-1)]
        return max(corners, key=lambda p: abs(p[0]-g[0]) + abs(p[1]-g[1]))

    def _telemetry(self, obs, phase, carrier, feed_count=0):
        if obs.turn % 25:
            return
        ca = 0 if carrier is None else obs.army_grid[carrier[0]][carrier[1]]
        share = ca / max(1, obs.my_army)
        sys.stderr.write(
            f"[doomstack_rusher] turn={obs.turn} phase={phase} carrier={ca} "
            f"share={share:.3f} my_army={obs.my_army} my_land={obs.my_land} "
            f"feeders={feed_count}\n")
        sys.stderr.flush()

    def act(self, obs):
        # Keep known general coordinates fresh.
        for r, c in self._owned(obs):
            if obs.type_grid[r][c] == 4:
                self.own_general = (r, c)
                break

        # Expansion phase produces broad territory and many 3-4 stacks. Switch
        # earlier when the board is already broad enough.
        if obs.turn < 90 and obs.my_land < 28:
            carrier = self._largest(obs)
            self._telemetry(obs, "expand", carrier)
            return self._expand(obs) or PASS

        if (self.rally is None or
            obs.owner_grid[self.rally[0]][self.rally[1]] != 1):
            self.rally = self._largest(obs)
        if self.rally is None:
            return PASS

        carrier_army = obs.army_grid[self.rally[0]][self.rally[1]]
        # Do not launch a small packet. Prefer a clear single dominant mass,
        # but ensure the stress test eventually transitions to attack.
        ready = carrier_army >= max(55, int(0.33 * max(1, obs.my_army)))
        forced = obs.turn >= 300 and carrier_army >= 35
        if ready or forced:
            self.attack = True

        if not self.attack:
            dist = self._owned_dist(obs, self.rally)
            feeders = []
            for p, d in dist.items():
                if p == self.rally or d <= 0:
                    continue
                a = obs.army_grid[p[0]][p[1]]
                if a < 3:
                    continue
                # Exactly the observed behaviour: even small 3-4 stacks are
                # worth collecting, larger distant stacks still get priority.
                utility = (a - 1) * 100 - d * 3
                feeders.append((utility, a, -d, p))
            self._telemetry(obs, "harvest", self.rally, len(feeders))
            if feeders:
                _, _, _, src = max(feeders)
                sd = dist[src]
                nexts = []
                r, c = src
                for direction, (dr, dc) in enumerate(DIRS):
                    p = (r + dr, c + dc)
                    if dist.get(p, 10**9) == sd - 1:
                        nexts.append((direction, p))
                if nexts:
                    direction, _ = min(nexts)
                    return (0, r, c, direction, 0)

            # If connected feeders are exhausted, expand with any spare stack;
            # this often connects new feeder regions to the rally component.
            move = self._expand(obs)
            if move is not None:
                return move
            # With no expansion route, launch what we have rather than idle.
            if carrier_army >= 20:
                self.attack = True
            else:
                return PASS

        # Attack: rally becomes the moving carrier. Re-lock if combat changed it.
        if obs.owner_grid[self.rally[0]][self.rally[1]] != 1:
            self.rally = self._largest(obs)
            if self.rally is None:
                return PASS
        carrier = self.rally
        self._telemetry(obs, "attack", carrier)
        if obs.army_grid[carrier[0]][carrier[1]] <= 1:
            self.rally = self._largest(obs)
            carrier = self.rally
            if carrier is None or obs.army_grid[carrier[0]][carrier[1]] <= 1:
                return PASS

        target = self._enemy_target(obs, carrier)
        step = self._path_step(obs, carrier, target)
        if step is None:
            return self._expand(obs) or PASS
        d = self._dir(carrier, step)
        r, c = carrier
        self.rally = step
        return (0, r, c, d, 0)
