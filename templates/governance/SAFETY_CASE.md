# Safety case: <target>

A structured argument, in [Goal Structuring Notation](https://scsc.uk/gsn) (GSN), that the
system is acceptably safe for a stated use. Each claim is supported by evidence or marked as
not supported; an honest "not supported" is the point of the exercise.

Notation: rectangles are goals (claims), parallelograms are strategies (how a claim is
broken down), rounded boxes are context, circles are solutions (evidence).

```mermaid
flowchart TD
    G1["G1: <system> is acceptably safe for <use> within <scope>"]
    C1("C1: scope and configuration")
    C2("C2: hazards: risk register")
    S1[/"S1: argue over each identified hazard"/]
    G2["G2: <claim for hazard group 1>"]
    G3["G3: <claim for hazard group 2>"]
    G4["G4: the evidence itself can be trusted"]
    Sn1(("Sn1: <test result>"))
    Sn2(("Sn2: <test result>"))
    Sn3(("Sn3: <grader calibration>"))

    G1 --- C1
    G1 --- C2
    G1 --> S1
    S1 --> G2 & G3 & G4
    G2 --> Sn1
    G3 --> Sn2
    G4 --> Sn3

    classDef supported fill:#d9f2d9,stroke:#2e7d32
    classDef partial fill:#fff3cd,stroke:#b8860b
    classDef unsupported fill:#f8d7da,stroke:#b02a37
```

Colour each goal: supported (green), partially supported (amber), not supported (red).

## Claims and evidence

| Goal | Claim | Evidence | Verdict |
|---|---|---|---|
| G2 | | | |

## Conclusion

<Acceptable / not acceptable for the stated use, and the gaps that block it.>
