import sys, os, json, zipfile, hashlib
from pathlib import Path
from urllib.parse import urlparse

def fail(folder, msg):
	print(f"Could not add mod in folder {folder}: {msg}")
	sys.stdout.flush()
	os._exit(0)

folder = Path(sys.argv[1])
author = sys.argv[2]

url = sys.argv[3]
repo = "/".join(Path(urlparse(url).path[1:]).parts[:2])
config_json = json.load(open("config.json", "r"))

def check_duplicates(mod_id, current_repo):
	try:
		repositories = config_json["repos"]

		for repo, mods in repositories.items():
			if repo != current_repo and mod_id in mods:
				fail(folder, f"A mod with the mod id \"{mod_id}\" already exists")
	except:
		fail(folder, "Internal error. This is very bad: config.json not found")

geode_file = folder / "mod.geode"
api_file = folder / "api.zip"

if not geode_file.exists():
	fail(folder, "Unable to find either mod or api")

try:
	archive = zipfile.ZipFile(geode_file, "r")
	mod_json_plaintext = archive.read("mod.json")
	mod_json = json.loads(mod_json_plaintext)
	archive_files = archive.namelist()

	mod_id = mod_json["id"]
	check_duplicates(mod_id, repo)

	platforms = []
	if f"{mod_id}.dylib" in archive_files:
		platforms.append("macos")
	if f"{mod_id}.dll" in archive_files:
		platforms.append("windows")
	if f"{mod_id}.so" in archive_files:
		platforms.append("android")
	if f"{mod_id}.ios.dylib" in archive_files:
		platforms.append("ios")

	entry_json = {
		"commit-author": author,
		"platforms": platforms,
		"mod": {
			"download": url + "mod.geode",
			"hash": hashlib.sha3_256(open(geode_file, "rb").read()).hexdigest()
		},
		"tags": mod_json.get("tags", [])
	}

	if api_file.exists():
		entry_json["api"] = {
			"download": url + "api.zip",
			"hash": hashlib.sha3_256(open(api_zip, "rb").read()).hexdigest()
		}
except:
	fail(folder, "Corrupted mod")
else:
	major_version = mod_json["version"].replace("v", "").split(".")[0]
	out_folder = Path("mods") / Path(mod_id + "@" + major_version)
	out_folder.mkdir(exist_ok=True)

	if "logo.png" in archive_files:
		open(out_folder / "logo.png", "wb").write(archive.read("logo.png"))
	if "about.md" in archive_files:
		open(out_folder / "about.md", "wb").write(archive.read("about.md"))
		
	json.dump(entry_json, open(out_folder / "entry.json", "w"), indent=4)
	open(out_folder / "mod.json", "wb").write(mod_json_plaintext)

	the_repo = config_json["repos"].get(repo, [])
	the_repo.append(mod_id)
	config_json["repos"][repo] = the_repo
	json.dump(config_json, open("config.json", "w"), indent=4)

	print(f"Successfully added {mod_id}")
