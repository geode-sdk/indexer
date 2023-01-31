import sys, os, shutil, json
from pathlib import Path
from urllib.parse import urlparse

repo = repo = "/".join(Path(urlparse(sys.argv[1]).path[1:]).parts[:2])
config = json.load(open("config.json", "r"))
repos = config["repos"]

if repo not in repos.keys():
	os._exit(0)


owned_mods = repos[repo]

for mod in Path("mods").iterdir():
	if not mod.is_dir():
		continue

	if mod.parts[-1].split("@")[0] in owned_mods:
		shutil.rmtree(mod, ignore_errors=True)

config["repos"][repo] = []
json.dump(config, open("config.json", "w"), indent=4)