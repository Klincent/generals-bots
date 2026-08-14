# V4.2 neural policy/value bot

V4.2 is a new standalone neural bot. V3.4 is used only as a bootstrap teacher and benchmark opponent; it is not a runtime fallback or architectural ceiling.

## Competition contract

- `GeneralsEnv(mode="competition")`
- rectangular 18..21 x 18..21 boards, represented in training as 21x21 plus a valid-cell mask
- fog of war
- truncation 1200
- build-castles enabled
- deathtouch from turn 800
- action space from the stdio protocol: PASS, BUILD(row,col), or MOVE(row,col,dir,split)

## Model v1

A small fully-convolutional residual policy/value network is deliberately chosen over the failed sparse hashed linear policy.

Input per cell:
- 6 type one-hot channels
- 3 owner one-hot channels
- log-scaled visible army
- own-army and opponent-army channels
- valid-cell mask
- broadcast global context: turn, my/opponent land, my/opponent army, army and land balance

Trunk:
- 32 channels
- 3x3 stem
- four 3x3 residual blocks

Policy head:
- 9 logits per cell: 4 directions x {FULL, HALF}, plus BUILD
- one global PASS logit
- total fixed action space: `21*21*9 + 1 = 3970`
- runtime/training legal-action masking

Value head:
- masked global average pooling
- MLP
- tanh scalar in [-1,1]

The initial network is intentionally small enough that custom C++ float inference is realistic later. Neural quality is proven in Python/JAX before spending effort on the final C++ inference implementation.

## Training stages

### Stage A: V3.4 bootstrap

Run exact corrected V3.4 vs itself under the real competition engine. Record both players' perspective-relative observations and exact actions. After the game, assign terminal value targets (+1/-1/0). Split train/validation by whole game seed.

This stage teaches legal movement, build timing, basic expansion and existing strong V3.4 behaviour without inheriting the old V4.1 hashed feature representation.

### Stage B: neural self-play / PPO-style actor-critic

Once imitation is stable and the neural agent can complete games without protocol/legality failures, collect vectorised neural self-play in the JAX environment. Fine-tune policy and value from terminal outcome plus GAE/advantage estimates. Maintain a small opponent league containing frozen recent checkpoints and V3.4 to limit catastrophic forgetting/exploitation loops.

### Stage C: league selection

Candidates must pass paired, common-RNG competition matches. The final untouched held-out range remains 30000..30499, twice per seed with seats swapped.

## Gates

1. smoke: teacher collection + tensor/action codec + one train step
2. bootstrap: validation policy top-1/top-k, value loss/correlation, zero invalid teacher labels
3. playable neural agent: zero crashes/protocol errors/invalid chosen actions
4. neural vs V3.4 validation outside final held-out seeds
5. self-play league improvement
6. final 1000-game held-out benchmark

## What V4.1 taught us

Do not train from toy continuation policies, heuristic top-8 candidate subsets, or a tiny additive feature vocabulary. V4.2 learns the full board representation and full legal action space. Training reports must expose dataset diversity, action-class distribution, train/validation-by-seed metrics, policy entropy, value metrics, and real game win rate.
