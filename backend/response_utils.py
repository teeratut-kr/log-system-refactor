from typing import Any


def remove_null_fields(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if item is None:
                continue
            cleaned_item = remove_null_fields(item)
            if cleaned_item is None:
                continue
            cleaned[key] = cleaned_item
        return cleaned

    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            if item is None:
                continue
            cleaned_item = remove_null_fields(item)
            if cleaned_item is None:
                continue
            cleaned_list.append(cleaned_item)
        return cleaned_list

    return value


def clean_log_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [remove_null_fields(item) for item in items]
