import sys
import json

author = sys.argv[1]

config = json.load(open("config.json", "r"))
print("YES" if author in config["verified"] else "NO")