import json
import os

def load_defaults(defaults_file):
    if os.path.exists(defaults_file):
        with open(defaults_file, "r") as f:
            return json.load(f)
    return {
        "url": None,
        "id": "130",
        "output": "output",
        "saving": False
    }

def save_defaults(data, defaults_file):
    with open(defaults_file, "w") as f:
        json.dump(data, f)

async def get_match_input(defaults_file: str = "defaults.json"):
    defaults = load_defaults(defaults_file)

    url = input(f"Masukkan URL (default: '{defaults['url']}' atau kosong): ") or defaults["url"]
    id = input(f"Masukkan ID (default: '{defaults['id']}'): ") or defaults["id"]
    output = input(f"Masukkan nama output (default: '{defaults['output']}'): ") or defaults["output"]

    saving_input = input(f"Simpan data? (y/n, default: {'y' if defaults['saving'] else 'n'}): ").lower()
    saving = saving_input == 'y' if saving_input in ['y', 'n'] else defaults["saving"]

    new_defaults = {
        "url": url,
        "id": id,
        "output": output,
        "saving": saving
    }
    save_defaults(new_defaults, defaults_file)

    return new_defaults

import json
import os

def load_ranking_defaults(defaults_file):
    if os.path.exists(defaults_file):
        with open(defaults_file, "r") as f:
            return json.load(f)
    return {
        "url": None,
        "ranking_option": "BWF World Tour Rankings",
        "output_dir": "output",
        "target_week": "latest"
    }

def save_ranking_defaults(data, defaults_file):
    with open(defaults_file, "w") as f:
        json.dump(data, f)

def get_ranking_input(defaults_file: str = "ranking_defaults.json"):
    ranking_defaults = load_ranking_defaults(defaults_file)

    url = input(f"Masukkan URL (default: '{ranking_defaults['url']}' atau kosong): ") or ranking_defaults["url"]
    ranking_option = input(f"Masukkan opsi ranking (default: '{ranking_defaults['ranking_option']}'): ") or ranking_defaults["ranking_option"]
    output_dir = input(f"Masukkan nama folder output (default: '{ranking_defaults['output_dir']}'): ") or ranking_defaults["output_dir"]
    target_week = input(f"Masukkan target week (default: '{ranking_defaults['target_week']}'): ") or ranking_defaults["target_week"]

    new_ranking_defaults = {
        "url": url,
        "ranking_option": ranking_option,
        "output_dir": output_dir,
        "target_week": target_week
    }
    save_ranking_defaults(new_ranking_defaults, defaults_file)

    print(f"url = {url}")
    print(f"ranking_option = {ranking_option}")
    print(f"output_dir = {output_dir}")
    print(f"target_week = {target_week}")

    return new_ranking_defaults
