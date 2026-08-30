from pathlib import Path


def load_config(path: str = "config.yml") -> dict:
    """Parse the deliberately small YAML subset used by this project."""
    result, section = {}, None
    for raw in Path(path).read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not line.startswith(" "):
            section = line[:-1]
            result[section] = [] if section in {"countries", "categories"} else {}
        elif line.strip().startswith("-"):
            result[section].append(line.strip()[1:].strip())
        else:
            key, value = (part.strip() for part in line.split(":", 1))
            try:
                value = float(value)
            except ValueError:
                pass
            result[section][key] = value
    return result
