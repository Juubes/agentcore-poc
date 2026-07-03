"""Third-party providers connectable through the portal."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    label: str
    tool: str  # gateway tool whose call triggers this provider's 3LO

    @property
    def key(self) -> str:
        # The /connect/<key> route. Derived from the tool's target prefix
        # because it MUST equal the gateway target name: the interceptor
        # rewrites un-onboarded elicitations to /connect/<target>.
        return self.tool.split("___", 1)[0]


PROVIDERS = {p.key: p for p in (
    Provider("GitHub", "github___listMyRepositories"),
)}
