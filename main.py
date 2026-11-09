"""A tiny command-line guide to useful campus services."""

from tools import find_resource, load_knowledge


def main():
    resources = load_knowledge()
    print("Welcome to CampusMate!")
    print("Try searching for a topic such as 'tutoring', 'library', or 'health'.")

    while True:
        topic = input("\nWhat do you need help with? (or type 'quit'): ").strip()
        if topic.lower() in {"quit", "exit", "q"}:
            print("Good luck with your studies!")
            break

        matches = find_resource(resources, topic)
        if not matches:
            print("I couldn't find a match. Try a broader word, like 'study' or 'health'.")
            continue

        for resource in matches:
            print(f"\n{resource['name']} - {resource['description']}")
            print(f"Contact: {resource['contact']}")


if __name__ == "__main__":
    main()
