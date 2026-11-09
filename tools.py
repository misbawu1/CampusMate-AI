"""Small reusable functions used by CampusMate."""

import json
from pathlib import Path


def load_knowledge():
    """Read the campus information stored beside this file."""
    file_path = Path(__file__).with_name("knowledge.json")
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def find_resource(resources, topic):
    """Return resources whose name, description, or keywords mention a topic."""
    search_term = topic.casefold()
    return [
        resource
        for resource in resources
        if search_term in resource["name"].casefold()
        or search_term in resource["description"].casefold()
        or any(search_term in word.casefold() for word in resource["keywords"])
    ]
