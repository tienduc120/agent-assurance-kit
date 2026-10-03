# Risk register: <target>

One row per hazard. Every control names the evidence that shows it works; a control without
evidence counts as no control.

| | |
|---|---|
| **Target** | <name, version, configuration under assessment> |
| **Scope** | <users, languages, channels, what the system may and may not do> |
| **Date / reviewer** | <date> / <name> |

## Scales

| Score | Likelihood (per conversation where the situation arises) | Impact |
|---|---|---|
| 1 | rare: not seen in testing, under 1% | negligible: mild confusion |
| 2 | unlikely: 1 to 5% | minor: unhelpful or slightly wrong |
| 3 | possible: 5 to 20% | moderate: misleading, privacy slip, policy breach |
| 4 | likely: 20 to 50% | major: unsafe advice, harmful content, data exposure |
| 5 | frequent: over 50% | severe: a person, especially a child, left at risk of harm |

Risk = likelihood × impact. **High** 15 or more, **medium** 8 to 14, **low** 7 or less.
Likelihood comes from measured rates where they exist (state the sample size).

## Register

| ID | Hazard | Category | L | I | Risk | Control | Evidence | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | <what can go wrong, for whom> | <OWASP / ATLAS / safety> | | | | <prevention or mitigation> | <link to results> | open / mitigated / accepted |
