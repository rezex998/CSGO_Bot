import sys
import requests

from lxml import html
from main import get_yaml, set_yaml

__author__ = "xoru"

def update_players(id = 0):
	"""Updates players and stores them in players.yaml.

	Data is fetched from HLTV.org.

	Args:
		id (int): ID to start incrementing from.
	Raises:
		TypeError: If id is not an integer.

	"""
	invalid = 0
	print("")
	while invalid < 50:
		id += 1

		print("\033[1A> ID: %s" % str(id))
		print("> ", end="\r")

		page = requests.get("http://www.hltv.org/?pageid=173&playerid=" + str(id)) # Overview page
		tree = html.fromstring(page.text)

		name = tree.xpath('(//div[normalize-space(text())="Primary team:"]/../../../div[1]/div[2])/text()')[0]
		maps_played = tree.xpath('(//div[normalize-space(text())="Maps played"]/../div[2])/text()')[0]

		if str(name) == "N/A":
			invalid += 1
			continue

		invalid = 0
		page = requests.get("http://www.hltv.org/?pageid=246&playerid=" + str(id)) # Match history page
		tree = html.fromstring(page.text)

		# Try/catch block for seeing if the player has a match on record
		try:
			latest_match = tree.xpath('(//div[normalize-space(text())="Team1"]/../../div[6]/div/div[1]/a)/text()')[0]
		except IndexError:
			# Nope... let's move on to the next player
			continue

		# Check if player has played at least one match in 2014 or later
		if int(maps_played) > 0 and int(latest_match.split()[1]) >= 14:
			players = get_yaml("players")
			if id not in players:
				players.update({id: str(name)})
				set_yaml("players", players)
				print("> Added player: %s (%s)            " % (str(name), str(id)), end="\r")

def update_teams(id = 0):
	"""Updates teams and stores them in teams.yaml.

	Data is fetched from HLTV.org.

	Args:
		id (int): ID to start incrementing from
	Raises:
		TypeError: If id is not an integer.

	"""
	invalid = 0
	print("")
	while invalid < 50:
		id += 1

		print("\033[1A> ID: %s" % str(id))
		print("> ", end="\r")

		page = requests.get("http://www.hltv.org/?pageid=179&teamid=" + str(id))
		tree = html.fromstring(page.text)

		name = tree.xpath('(//div[contains(text(), "Team stats: ")])/text()')[0].replace("Team stats: ", "").strip()
		maps_played = tree.xpath('(//div[normalize-space(text())="Maps played"]/../div[2])/text()')[0]

		if str(name) == "No team":
			invalid += 1
			continue

		invalid = 0
		page = requests.get("http://www.hltv.org/?pageid=188&teamid=" + str(id))
		tree = html.fromstring(page.text)

		try:
			latest_match = tree.xpath('(//div[normalize-space(text())="Team1"]/../../div[6]/div/a[1]/div)/text()')[0]
		except IndexError:
			continue

		# Check if team has played at least one match in 2014 or later.
		if int(maps_played) > 0 and int(latest_match.split()[1]) >= 14:
			teams = get_yaml("teams")
			if id not in teams:
				teams.update({id: {"names": [str(name)]}})
				set_yaml("teams", teams)
				print("> Added team: %s (%s)            " % (str(name), str(id)), end="\r")

if __name__ == "__main__":
    try:
        print("> Updating players...")
        update_players()

        print("> Updating teams...")
        update_teams()
		sys.exit(1)
    except KeyboardInterrupt:
        print("> Update forcefully quit.")
        sys.exit(1)