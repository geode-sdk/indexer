import json
import hashlib
import os
import sys
import zipfile
import urllib.request
import re
from pathlib import Path
import subprocess

def fail(msg):
	print(f'Fail: {msg}', file=sys.stderr)
	sys.exit(1)


index_path = Path(sys.argv[1])
issue_author = sys.argv[2]
if len(sys.argv) == 3:
	issue_body = os.environ['ISSUE_BODY']
else:
	# not passing issue body as a system argument for injection reasons
	# but its still here for testing
	issue_body = sys.argv[3]

is_old = sys.argv[4] == 'old' if len(sys.argv) > 4 else False

if 'Your mod link' not in issue_body and not is_old:
	print('Not a valid index entry', file=sys.stderr)
	sys.exit(2)

# Download the geode file
try:
	match = re.search(r'\s*?### Your mod link\s*?(\S+)\s*?', issue_body);
	if match:
		mod_url = match.group(1)
		urllib.request.urlretrieve(mod_url, 'mod.geode')
	else:
		fail(f'Could not find the geode link')

except Exception as inst:
	fail(f'Could not download the geode file: {inst}')

# Validate the geode file
try:
	archive = zipfile.ZipFile('mod.geode', 'r')
	mod_json = json.loads(archive.read('mod.json'))
	mod_id = mod_json['id']
	mod_version = mod_json['version'].replace('v', '')

	file_list = archive.namelist()	

except Exception as inst:
	fail(f'Not a valid geode file: {inst}')


# Populate entry.json
try:
	mod_platforms = []
	if f"{mod_id}.dylib" in file_list:
		mod_platforms.append("macos")
	if f"{mod_id}.dll" in file_list:
		mod_platforms.append("windows")
	if f"{mod_id}.android32.so" in file_list:
		mod_platforms.append("android32")
	if f"{mod_id}.android64.so" in file_list:
		mod_platforms.append("android64")
	if f"{mod_id}.ios.dylib" in file_list:
		mod_platforms.append("ios")

	mod_tags = mod_json.get("tags", [])
	mod_data = open("mod.geode", "rb").read()
	mod_hash = hashlib.sha256(mod_data).hexdigest()

	# for backwards compatibility
	old_mod_hash = hashlib.sha3_256(mod_data).hexdigest()

	entry_json = {
		"commit-author": issue_author,
		"platforms": mod_platforms,
		"mod": {
			"download": mod_url,
			"hash": old_mod_hash,
			"hash256": mod_hash
		},
		"tags": mod_tags
	}
except Exception as inst:
	fail(f'Could not populate entry.json: {inst}')



# Update the config.json
try:
	config_json = json.load(open(index_path / 'config.json', 'r'))

	if 'entries' not in config_json:
		config_json['entries'] = {}

	if mod_id not in config_json['entries']:
		config_json['entries'][mod_id] = {}

	config_entry = config_json['entries'][mod_id]

	if 'verified' not in config_entry:
		config_entry['verified'] = False

	if 'versions' in config_entry:
		config_versions = config_entry['versions']
	else:
		config_versions = []

	if config_versions:
		old_version = config_versions[-1]
	else:
		old_version = None

	if mod_version not in config_versions:
		config_versions.append(mod_version)
	else:
		# replacing existing ver :grimacing:
		old_version = mod_version

	config_entry['versions'] = config_versions

	json.dump(config_json, open(index_path / 'config.json', 'w'), indent=4)

except Exception as inst:
	fail(f'Could not populate config.json: {inst}')



def write_general_files(general_path):
	if 'logo.png' in file_list:
		archive.extract('logo.png', path=general_path)
		logo_path = (general_path / 'logo.png').as_posix()
		# resize mod logos
		subprocess.call(['convert', logo_path, '-resize', '336x336>', logo_path])
	if 'about.md' in file_list:
		archive.extract('about.md', path=general_path)
	if 'changelog.md' in file_list:
		archive.extract('changelog.md', path=general_path)


def write_version_files(version_path):
	json.dump(entry_json, open(version_path / 'entry.json', 'w'), indent=4)
	archive.extract('mod.json', path=version_path)


# Very sad code i know
def compare_versions(version1, version2):
	if '-' not in version1:
		version1 += '?'
	if '-' not in version2:
		version2 += '?'

	return version1 > version2


# Fill the directory
try:
	mod_directory = index_path / 'mods-v2' / mod_id
	version_mod_directory = mod_directory / mod_version
	version_mod_directory.mkdir(parents=True, exist_ok=True)

	write_version_files(version_mod_directory)

	latest_version = mod_version
	for version in config_versions:
		if compare_versions(version, latest_version):
			latest_version = version

	if mod_version == latest_version:
		write_general_files(mod_directory)
except Exception as inst:
	fail(f'Could not populate mod folder {version_mod_directory}: {inst}')

def send_webhook(mod_id, new_version, old_version=None):
	from urllib import request
	import json
	import os

	COLOR = 0x8d73ce

	issue_author = os.getenv('ISSUE_AUTHOR', '?')
	comment_author = os.getenv('COMMENT_AUTHOR', '?')

	description = f'''https://geode-sdk.org/mods/{mod_id}

Uploaded by: [{issue_author}](https://github.com/{issue_author})
Accepted by: [{comment_author}](https://github.com/{comment_author})'''

	if new_version == old_version:
		title = f'Replaced? `{mod_id}` {new_version}'
	elif old_version is None:
		title = f'Added `{mod_id}` {new_version}'
		description = 'New mod!\n' + description
	else:
		title = f'Updated `{mod_id}` {old_version} -> {new_version}'

	embeds = [
		{
			'color': COLOR,
			'title': title,
			'description': description,
			'thumbnail': {
				'url': f'https://raw.githubusercontent.com/geode-sdk/mods/main/mods-v2/{mod_id}/logo.png'
			}
		}
	]

	req = request.Request(os.getenv('DISCORD_WEBHOOK_URL'), method='POST')
	req.add_header('User-Agent', 'python urllib')
	req.add_header('Content-Type', 'application/json')
	data = {
		'content': None,
		'embeds': embeds,
	}
	request.urlopen(req, data=json.dumps(data).encode('utf-8'))

print(f'''## Info:
* Mod ID: `{mod_id}`
* Version: `{mod_version}`
* Targetting GD: `{mod_json['gd']}`
* Actual platforms: `{mod_platforms}`
* Targetting Geode: `{mod_json['geode']}`
''')

potential_issues = []
if old_version == mod_version:
	potential_issues.append(f'Replacing an existing version `{mod_version}`')
if mod_json['gd'] == '*':
	potential_issues.append(f'Targetting *any* GD version, make sure you really support that.')

def check_bad_about():
	if not (mod_directory / 'about.md').exists():
		return True
	else:
		with open(mod_directory / 'about.md', 'r') as file:
			contents = file.read().strip()
		lines = contents.splitlines()
		if len(lines) == 3 and lines[-1].lower().strip() == 'edit about.md to change this':
			return True
	return False

if check_bad_about():
	potential_issues.append('Missing/unchanged `about.md`. Please consider writing one to let the user know what they are downloading.')

# TODO: check for unchanged logo.png

if potential_issues:
	print('## Potential issues')
	print('\n'.join(f'* {x}' for x in potential_issues))

	if os.getenv('GITHUB_OUTPUT'):
		with open(os.getenv('GITHUB_OUTPUT'), 'a') as file:
			file.write('has_issues=YES\n')


# mod only gets auto accepted when there are no issues
try:
	# ignore potential issues if this is triggered by a staff !accept command
	if (os.getenv('ACTUALLY_ACCEPTING') == 'YES' or not potential_issues) and os.getenv('VERIFY_USER_RESULT') == 'YES':
		send_webhook(mod_id, old_version=old_version, new_version=mod_version)
	else:
		with open('silly_log.txt', 'a') as file:
			file.write("not sending webhook :P\n")
except Exception as e:
	# dont care about webhook failing
	with open('silly_log.txt', 'a') as file:
		file.write(str(e) + "\n")