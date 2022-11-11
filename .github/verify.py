import sys
import json

author = sys.argv[1]

config = json.load(open("config.json", "r"))
print("true" if author not in config["verified"] else "false")