from typing import Dict, Optional

DEMO_USERS: Dict[str, Dict[str, Optional[str]]] = {
    "admin1": {"role": "admin", "tenant": None},
    "viewerA": {"role": "viewer", "tenant": "demoA"},
    "viewerB": {"role": "viewer", "tenant": "demoB"},
}


def available_users() -> list[str]:
    return list(DEMO_USERS.keys())
