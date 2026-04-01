BACKEND_USERS = ["admin1", "viewerA", "viewerB"]
USER_DIRECTORY = {
    "admin1": {"role": "admin", "tenant": "All", "display": "admin"},
    "viewerA": {"role": "viewer", "tenant": "demoA", "display": "viewerA"},
    "viewerB": {"role": "viewer", "tenant": "demoB", "display": "viewerB"},
}
LOGIN_CREDENTIALS = {
    "admin": {"password": "admin", "backend_user": "admin1"},
    "viewerA": {"password": "viewerA", "backend_user": "viewerA"},
    "viewerB": {"password": "viewerB", "backend_user": "viewerB"},
}


def role_label(profile: dict[str, str]) -> str:
    return "Administrator" if profile["role"] == "admin" else "Viewer"
