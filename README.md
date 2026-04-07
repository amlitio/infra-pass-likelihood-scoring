## Quick start

```bash
git clone https://github.com/amlitio/infra-pass-likelihood-scoring.git
cd infra-pass-likelihood-scoring
python scoring.py --demo
```

## How to run

### Option 1: Demo mode

```bash
python scoring.py --demo
```

### Option 2: Pass all fields as flags

```bash
python scoring.py \
  --procedural-stage 20 \
  --sponsor-strength 9 \
  --funding-clarity 12 \
  --route-specificity 10 \
  --need-case 10 \
  --row-tractability 7 \
  --local-plan-alignment 6 \
  --opposition-drag 2 \
  --land-monetization-fit 14
```

### Option 3: Use a JSON input file

Create `project.json`:

```json
{
  "procedural_stage": 20,
  "sponsor_strength": 8,
  "funding_clarity": 10,
  "route_specificity": 8,
  "need_case": 10,
  "row_tractability": 7,
  "local_plan_alignment": 6,
  "opposition_drag": 2,
  "land_monetization_fit": 12
}
```

Run:

```bash
python scoring.py --input-json project.json
```

## Output

The CLI prints:
1. Category-by-category breakdown (with opposition as a negative contribution)
2. Final score on 0-100
3. Interpretation band:
   - 85-100: very high probability / very actionable
   - 70-84: strong watchlist candidate
   - 55-69: speculative but worth targeted hunting
   - below 55: mostly informational, not land-first actionable

## Tests

Run unit tests:

```bash
python -m unittest test_scoring.py
```

~~~

### Scoring inputs

The model uses these categories:

- procedural stage (0-25)
- sponsor strength (0-10)
- funding clarity (0-15)
- route specificity (0-10)
- need case / demand pull (0-10)
- right-of-way tractability (0-10)
- local-plan alignment (0-8)
- opposition/environmental drag (0-7, subtracted)
- land monetization fit (0-19)

Final formula:

`A + B + C + D + E + F + G + I - H`
