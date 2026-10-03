# Methods

Learn Signal does exact expected-value arithmetic on a finite decision table. It estimates nothing from data: every probability, payoff, cost and study accuracy is an input you supply and review.

## Notation

- scenarios `s` with prior probabilities `p(s)`, mutually exclusive and summing to 1;
- options `a` with net payoffs `u(a, s)`, all in one unit and horizon, higher is better;
- studies `t` with cost `c_t` and possible results `y`, each with a probability `L_t(y | s)` in every scenario; for each study and scenario these sum to 1;
- questions `q`, each giving every scenario an answer `q(s)`.

## 1. Audit and review

The model is checked against a strict schema: required fields, number ranges, unique reference codes, references that resolve, one payoff per option × scenario, and probabilities that total 1 (no automatic renormalisation). Calculation is withheld until every prior and payoff is known and a person has recorded a review. The review stores a SHA-256 fingerprint of the inputs; any later edit clears it.

## 2. Deciding now

```
EV(a)       = Σ_s p(s) u(a, s)
V_now       = max_a EV(a)
EOL(a)      = V_perfect − EV(a)
```

The preferred option has the highest expected payoff; options within numerical tolerance of it are shown as a tie. Expected opportunity loss is how much an option falls short, on average, of what perfect information would allow.

## 3. Perfect information (EVPI)

```
V_perfect   = Σ_s p(s) max_a u(a, s)
EVPI        = V_perfect − V_now
```

EVPI is the most any study could be worth under the model, because no study can do better than revealing the true scenario. It is zero when the same option is best in every scenario.

## 4. A specific study (EVSI)

For each result `y` of study `t`:

```
joint(s, y)     = p(s) L_t(y | s)
P(y)            = Σ_s joint(s, y)
p(s | y)        = joint(s, y) / P(y)                       (Bayes' rule)
best after y    = argmax_a Σ_s p(s | y) u(a, s)
V_t             = Σ_y max_a Σ_s joint(s, y) u(a, s)
EVSI_t          = V_t − V_now
net value_t     = EVSI_t − c_t
```

EVSI lies between 0 and EVPI. A study is only worth something if at least one of its results would change the preferred option. A perfectly accurate study reaches EVPI; a study whose results are equally likely in every scenario is worth 0. A result with `P(y) = 0` is reported as impossible under the model, with no posterior. A study with missing result probabilities or cost is listed but not valued.

Each study is valued alone, decided on before the main decision, and with its full cost. Net values cannot be added across studies, and the app does not plan sequences of studies, combinations or sample sizes.

## 5. Questions (perfect partial information)

A question groups scenarios by its answer. Learning the answer perfectly is worth

```
V_q   = Σ_answers max_a Σ_{s: q(s) = answer} p(s) u(a, s)
value = V_q − V_now
```

A question whose answer separates every scenario is worth EVPI; one with the same answer everywhere is worth 0. Values of different questions overlap and are not additive.

## 6. Sensitivity to a prior

One scenario's prior is set to 41 values from 0 to 1 (steps of 0.025). The other scenarios keep their relative probabilities, scaled to fill the rest. For each point the app recomputes the best expected payoff, EVPI and the preferred option, and lists the grid points where the preferred option changes. The exact switch point can lie between grid points. This is a one-dimensional check on an assumption, not a confidence interval.

## Worked example

The fictional demo (NOK contribution over 12 months; prior 0.4 for higher demand):

| Option | Higher demand | Lower demand | Expected payoff |
|---|---|---|---|
| Full launch | 140,000 | −60,000 | 20,000 |
| Small pilot | 50,000 | −10,000 | 14,000 |
| Hold | 0 | 0 | 0 |

- `V_now` = 20,000 (Full launch). `V_perfect` = 0.4 × 140,000 + 0.6 × 0 = 56,000, so EVPI = 36,000.
- Structured demand test, positive with probability 0.8 if demand is higher and 0.2 if lower: P(positive) = 0.44, P(higher | positive) = 0.32 / 0.44 ≈ 0.727, so launch; after a negative result, P(higher | negative) = 0.08 / 0.56 ≈ 0.143, so hold. `V_t` = 37,600, EVSI = 17,600, net of its 8,000 cost 9,600.
- Exploratory survey at 55% accuracy: after a negative result the pilot (joint 5,700) narrowly beats launch (5,400), so the survey can change the decision, but EVSI is only 300, and after its 3,000 cost it loses 2,700.

The test suite also checks a classic textbook oil-drilling decision worked by hand: prior 0.25 for oil, drill pays 700 or −100, selling pays 90, and a survey costing 30 reads favourable with probability 0.6 if oil and 0.2 if dry. EVPI is 142.5, EVSI 53 and the survey's net value 23.

## Assumptions and limits

- Risk-neutral expected value. With money payoffs, a risk-averse decision maker may value information differently; to reflect risk attitude, enter utilities as payoffs and express study costs in the same utility units.
- The study does not change the outcomes it measures, causes no delay that changes payoffs, and its cost is incurred whatever the result.
- Scenarios are exhaustive and exclusive. Unlisted possibilities, and correlated uncertainties not combined into joint scenarios, are outside the model.
- All values are conditional on the reviewed inputs. The app does not check whether a prior or an accuracy figure is realistic; the sensitivity check and the sources behind each input are there for that.
