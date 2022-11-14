import sys, os, shutil, json
from pathlib import Path

repo = repo = "/".join(Path(urlparse(sys.argv[1]).path[1:]).parts[:2])
repos = json.load(open("config.json", "r"))["repos"]

if repo not in repos.keys():
	os._exit(0)


owned_mods = repos[repo]

for mod in pathlib.Path(".").iter_dir():
	if not mod.is_dir():
		continue

	if mod.parts[-1].split("@")[0] in owned_mods:
		shutil.rmtree(mod, ignore_errors=True)

repos[repo] = []
json.dump(repos, open("config.json", "w"), indent=4)