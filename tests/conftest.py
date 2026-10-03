from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCK_SAFE = ROOT / "examples" / "mock" / "target.yaml"
MOCK_VULNERABLE = ROOT / "examples" / "mock" / "target-vulnerable.yaml"
PIKAPI = ROOT / "engagements" / "pikapi" / "target.yaml"
