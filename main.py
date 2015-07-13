import os
import re
import sys
import bot
import yaml
import json
import praw
import requests
import datetime
import configparser

from lxml import html
from operator import itemgetter

subreddit = "csgobetting"
__author__ = "xoru"
__version__ = "1.3-beta"
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + '/'


def get_nth_item(number, list):
	"""Gets the nth item in a list/dict.

	Args:
		number (int): nth item of list to return.
		list (list/dict): List with items.
	Raises:
		TypeError: If list is not iterable.
	Returns:
		The Python object found in list, None otherwise.

	"""
	i = 0
	for item in list:
		i += 1
		if i == number:
			return item
	return None

def file_string_exists(file, s):
	"""Checks if s exists in file.

	Args:
		file (str): The file to search, typically a TXT file.
		s (str): The string to search for.
	Returns:
		A boolean which will be True if s is found on its own line in file, False
		otherwise.
	Raises:
		FileNotFoundError: If file is not found.
		TypeError: If file is not a string.
		AttributeError: If s is not a string.

	"""
	with open(__location__ + file) as f:
		for l in f:
			l = l.rstrip().lower()
			if l == s.lower():
				return True
	return False

def file_string_append(file, s):
	"""Appends s to end of file.

	Args:
		file (str): The file where s will be appended.
		s (str): The string to be appended.
	Raises:
		FileNotFoundError: If file is not found.
		TypeError: If file or s is not a string.

	"""
	with open(__location__ + file, 'a') as f:
		f.write(s + '\n')

def file_string_remove(file, s):
	"""Removes s from file.

	Args:
		file (str): The file from where s will be removed.
		s (str): The string to be removed.
	Raises:
		FileNotFoundError: If file is not found.
		TypeError: If file or s is not a string.

	"""
	lines = None
	with open(__location__ + file) as f:
		lines = f.readlines()
	with open(__location__ + file, 'w') as f:
		for line in lines:
			if line != s + '\n':
				f.write(line)

def get_yaml(filename):
	"""Gets the content of a YAML file.

	Args:
		filename (str): The filename of the .yaml file to retrieve.
	Raises:
		FileNotFoundError: If file is not found.
	Returns:
		A Python object.

	"""
	with open(__location__ + filename + ".yaml") as f:
		file = yaml.load(f)
	if not file:
		return []
	return file

def set_yaml(filename, data):
	"""Dumps data to a YAML file.

	Args:
		filename (str): The filename of the .yaml file to set.
		data (obj): Data to dump. Typically a dict.
	Raises:
		FileNotFoundError: If file is not found.

	"""
	with open(__location__ + filename + ".yaml", "w") as f:
		yaml.dump(data, f, default_flow_style=False)

def add_csgonuts(teams):
	"""Adds 'csgonuts' key to teams that are in csgonuts.txt.

	csgonuts.txt is filled with a simple web-scraper.

	Args:
		teams (dict): Full team list, typically provided from get_yaml("teams").

	"""
	found = {}
	for team in teams:
		for name in teams[team]['names']:
			team_name = name.replace(" ", "")
			if file_string_exists('csgonuts.txt', team_name):
				found.update({team: team_name})
				file_string_remove('csgonuts.txt', team_name)
				break

	for team in found:
		teams[team]['csgonuts'] = found[team]

	set_yaml('teams', teams)

def update_teams(id = 0):
	"""Updates teams and stores them in teams.yaml.

	Data is fetched from HLTV.org.

	Args:
		id (int): ID to start incrementing from
	Raises:
		TypeError: If id is not an integer.

	"""
	# TODO: Update this old function. (and update_players())
	invalid = 0
	while invalid < 50:
		id += 1
		page = requests.get("http://www.hltv.org/?pageid=179&teamid=" + str(id))
		tree = html.fromstring(page.text)

		name = tree.xpath('(//div[contains(text(), "Team stats: ")])/text()')[0].replace("Team stats: ", "").strip()
		maps_played = tree.xpath('(//div[normalize-space(text())="Maps played"]/../div[2])/text()')[0]

		if str(name) == "No team":
			invalid += 1
			bot.log("No team found")
			continue

		invalid = 0
		page = requests.get("http://www.hltv.org/?pageid=188&teamid=" + str(id))
		tree = html.fromstring(page.text)

		latest_match = tree.xpath('(//div[normalize-space(text())="Team1"]/../../div[6]/div/a[1]/div)/text()')[0]

		# Check if team has played at least one match in 2014 or later.
		if int(maps_played) > 0 and int(latest_match.split()[1]) >= 14:
			teams = get_yaml("teams")
			if id not in teams:
				teams.update({id: {"names": [str(name)]}})
				set_yaml("teams", teams)

def update_players(id = 0):
	"""Updates players and stores them in players.yaml.

	Data is fetched from HLTV.org.

	Args:
		id (int): ID to start incrementing from.
	Raises:
		TypeError: If id is not an integer.

	"""
	invalid = 0
	while invalid < 50:
		id += 1

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
			players.update({id: str(name)})
			set_yaml("players", players)
			bot.log("Added " + str(name))

def find_teams(text, teams, case_sensitive = False):
	"""Finds team names and abbreviations in a text.

	Args:
		text (str): Text to search.
		teams (dict): Full team list, typically provided from get_yaml("teams").
		case_sensitive (bool): If search should be case sensitive with team names.
	Raises:
		TypeError: If text is not a string. If teams is not a dict.
	Returns:
		A list of the found team's ID's,

	"""
	if text is None:
		return None

	found_teams = []
	# Remove '/', as it is often used in titles such as "Team1 vs Winner of Team2/Team3"
	text = text.replace("/", " ")

	for team in teams:
		for name in teams[team]['names']:
			if not case_sensitive:
				name = name.lower()
				text = text.lower()

			if " " in name:
				if name in text:
					found_teams.append(team)
					break
			else:
				text_split = text.split()
				if name in text_split:
					found_teams.append(team)
					break
	return found_teams

def find_players(text, players, case_sensitive = False):
	"""Find player names in a text.

	Args:
		text (str): Text to search.
		players (dict): Full player list, typically provided from get_yaml("players")
		case_sensitive (bool): If search should be case sensitive with player names.
	Raises:
		TypeError: If text is not a string. If players is not a dict.
	Returns:
		A list of the found player's id's.

	"""
	if text is None:
		return None

	if not case_sensitive:
		text = text.lower()

	found_players = []
	text = text.replace(",", " ").replace(".", " ").replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")

	for player in players:
		name = players[player]
		if not case_sensitive:
			name = name.lower()

		if name in text.split() or (" " in name and name in text):
			found_players.append(player)
	return found_players

def get_player_stats(players, all_players):
	"""Gets player statistics from HLTV.

	Args:
		players (list): List of players to get statistics on.
		all_players (dict): Full player list, typically provided by get_yaml("players").
	Raises:
		TypeError: If players is not a list. If all_players is not a dict.
	Returns:
		A list of dicts, one dict for each player. The dict contains statistics about
		the player.

	"""
	player_stats = []
	for player in players:
		url = "http://www.hltv.org/?pageid=173&playerid=" + str(player) # Overview page
		page = requests.get(url)
		tree = html.fromstring(page.text)

		team = tree.xpath('(//div[normalize-space(text())="Primary team:"]/../div[2]/a)/text()')[0]
		team_url = tree.xpath('(//div[normalize-space(text())="Primary team:"]/../div[2]/a)/@href')[0]
		rating = tree.xpath('(//div[normalize-space(text())="Rating"]/../div[2])/text()')[0]
		total_kills = tree.xpath('(//div[normalize-space(text())="Total kills"]/../div[2])/text()')[0]
		total_deaths = tree.xpath('(//div[normalize-space(text())="Total deaths"]/../div[2])/text()')[0]
		kd_ratio = tree.xpath('(//div[normalize-space(text())="K/D Ratio"]/../div[2])/text()')[0]
		kills_per_round = tree.xpath('(//div[normalize-space(text())="Average kills per round"]/../div[2])/text()')[0]

		stats = {
			'name':            all_players[player],
			'url':             url,
			'team':            team,
			'team_url':        team_url,
			'rating':          rating,
			'total_kills':     total_kills,
			'total_deaths':    total_deaths,
			'kd_ratio':        kd_ratio,
			'kills_per_round': kills_per_round
		}
		player_stats.append(stats)

	# Sort by rating by default
	player_stats = sorted(player_stats, key=itemgetter('rating'), reverse=True)
	return player_stats

def get_team_stats(teams, all_teams):
	"""Gets team statistics from HLTV.

	Args:
		teams (list): List of teams to get statistics on.
		all_teams (dict): Full team list, typically provided by get_yaml("teams").
	Raises:
		TypeError: If teams is not a list. If all_teams is not a dict.
	Returns:
		A list of dicts, one dict for each team. The dict contains statistics about
		the team.

	"""
	team_stats = []
	for team in teams:
		url = "http://www.hltv.org/?pageid=179&teamid=" + str(team) # Overview page
		page = requests.get(url)
		tree = html.fromstring(page.text)
		main_div = 12

		maps_played = tree.xpath('(//div[normalize-space(text())="Maps played"]/../div[2])/text()')[0]
		wdl = tree.xpath('(//div[normalize-space(text())="Wins / draws / losses"]/../div[2])/text()')[0].replace(" ", "").split("/")
		total_played = int(wdl[0]) + int(wdl[2])
		win_percentage = str(round((int(wdl[0]) / total_played) * 100)) + "%"

		stats = {
			'name':              all_teams[team]['names'][0],
			'url':               url,
			'maps_played':       maps_played,
			'wins_draws_losses': win_percentage,
			'recent_matches':    []
		}

		page = requests.get("http://www.hltv.org/?pageid=188&teamid=" + str(team)) # Match history page
		tree = html.fromstring(page.text)

		for match in range(5):
			i = 6 + (match * 2)
			try:
				match_link = tree.xpath('//div[normalize-space(text())="Team1"]/../../div[' + str(i) + ']/div/a[1]/@href')[0]

				match_team1 = tree.xpath('//div[normalize-space(text())="Team1"]/../../div[' + str(i) + ']/div/a[2]/div/text()')[0]
				match_team1 = match_team1[match_team1.index("(") + 1:match_team1.rindex(")")] # Get text inside parentheses

				match_team2 = tree.xpath('//div[normalize-space(text())="Team1"]/../../div[' + str(i) + ']/div/a[3]/div/text()')[0]
				match_team2 = match_team2[match_team2.index("(") + 1:match_team2.rindex(")")]

				match = {
					'url':  "http://www.hltv.org" + match_link,
					'team1': match_team1,
					'team2': match_team2
				}

				stats['recent_matches'].append(match)
			except IndexError:
				break
		team_stats.append(stats)

	# Sort by maps_played by default
	team_stats = sorted(team_stats, key=itemgetter('maps_played'), reverse=True)
	return team_stats

def get_matchup(team1, team2):
	"""Gets matchup statistics between two teams from CSGOnuts.

	Args:
		team1 (dict): First team. Dict of team from get_yaml("teams").
		team2 (dict): Second team. Dict of team from get_yaml("teams").
	Raises:
		TypeError: If team1 or team2 are not dictionaries.
	Returns:
		A dictionary with statistics if successful, None otherwise.

	"""
	if not team1 or not team2 or ('csgonuts' not in team1 or 'csgonuts' not in team2):
		return None

	page = requests.get("http://www.csgonuts.com/history?t1=" + team1['csgonuts'] + "&t2=" + team2['csgonuts'])
	tree = html.fromstring(page.text)

	try:
		# If the two teams have not played against each other.
		error_message = tree.xpath('(//div[contains(text(), "We have no record of match between")])/text()')[0]
		return None
	except IndexError:
		pass

	# If we have been redirected (Should only happen if a team does not exist).
	if page.history:
		bot.log("page.history is not empty. " + team1['csgonuts'] + " or " + team2['csgonuts'] + " does not exist on csgonuts.")
		return None

	matches_played = tree.xpath('(/html/body/div/div[2]/div[2]/div[2]/div[3]/div/div[1]/p[1]/span)/text()')[0]
	matches_played = re.sub(r'\([^)]*\)', '', matches_played)
	win_percentage = tree.xpath('(/html/body/div/div[2]/div[2]/div[2]/div[3]/div/div[1]/p[2]/span)/text()')[0]

	maps = {}
	# Fetch map statistics
	for i in range(6):
		try:
			map_name = tree.xpath('(/html/body/div/div[2]/div[2]/div[2]/div[3]/div/div[' + str(i + 2) + ']/div[1]/a/span)/text()')[0]
			map_win = tree.xpath('(/html/body/div/div[2]/div[2]/div[2]/div[3]/div/div[' + str(i + 2) + ']/div[2]/span)/text()')[0]
			maps.update({map_name: map_win})
		except IndexError:
			break

	matchup = {
		'matches_played': matches_played,
		'win_percentage': win_percentage,
		'maps':           maps
	}

	return matchup

def construct_comment(found_teams, found_players, all_teams, all_players, strawpoll = None, is_root = False, edited_by = None):
	"""Magically put everything together into Markdown syntax.

	Args:
		found_teams (list): List of teams to include in the "Teams" table.
		found_players (list): List of players to include in the "Players" table.
		all_teams (dict): Full team list, typically provided from get_yaml("teams").
		all_players (dict): Full player list, typically provided from get_yaml("players").
		strawpoll (str): URL to strawpoll.
		is_root (bool): If comment is a top-level-comment (no parents).
		edited_by (str): Username of last redditor who edited the comment via commands.
	Raises:
		TypeError: If all_teams or all_players are not dictionaries. If strawpoll is not
			a string. If found_teams or found_players are not lists.
	Returns:
		A string with Markdown syntax for posting on reddit.

	"""
	if not found_teams and not found_players:
		return None

	comment = ""
	player_stats = None
	team_stats = None

	if found_players:
		comment += "###Player Stats\n"
		comment += "Player Name|Team|Rating [(?)](http://www.hltv.org/?pageid=242)|Total K/D|K/D Ratio|Kills per round\n:|:|:|:|:|:|:\n"

		player_stats = get_player_stats(found_players, all_players)

		for player in player_stats:
			comment += (
				"[" + player['name'] + "](" + player['url'] + ")|" +
				"[" + player['team'] + "](" + player['team_url'] + ")|" +
				player['rating'] + "|" +
				player['total_kills'] + "/" + player['total_deaths'] + "|" +
				player['kd_ratio'] + "|" +
				player['kills_per_round'] + "\n"
			)

	if found_teams:
		comment += "\n###Team Stats\n"
		comment += "Team Name|Maps Played|Won|Recent matches\n:|:|:|:\n"

		team_stats = get_team_stats(found_teams, all_teams)

		for team in team_stats:
			recent_matches = (", ".join("[**" + match['team1'] + "**-" + match['team2'] + "](" + match['url'] + ")" for match in team['recent_matches']))
			comment += (
				"[" + team['name'] + "](" + team['url'] + ")|" +
				team['maps_played'] + "|" +
				team['wins_draws_losses'] + "|" +
				recent_matches + "\n"
			)

	matchup_team1 = all_teams[get_nth_item(1, found_teams)]
	matchup_team2 = all_teams[get_nth_item(2, found_teams)]
	matchup = get_matchup(matchup_team1, matchup_team2)

	if matchup:
		comment += (
			"\n###Matchup\n\n" +
			matchup['matches_played'] + "\n\n" +
			matchup['win_percentage'] + "\n\n" +
			"Map|Winner\n:|:\n"
		)

		for map_name in matchup['maps']:
			comment += map_name + "|" + matchup['maps'][map_name] + "\n"

	elif matchup_team1 and matchup_team2:
		comment += "\n###Matchup\n\n" + matchup_team1['names'][0] + " and " + matchup_team2['names'][0] + " have not played against each other before."

	comment += "\n"

	if strawpoll:
		comment += "\n###[Strawpoll](" + strawpoll + ")"

	if is_root:
		# If no or less than 10 players (or 2 teams) are found, add a notice.
		if not player_stats or len(player_stats) < 10 or not team_stats or len(team_stats) < 2:
			comment += "\n^(Missing players/teams detected. This could be due to there not being any information on them on HLTV.)\n"

	comment += "\n^(**Note:** Adding irrelevant players or teams will result in being added to the bot ignore list without warning.)\n"

	if edited_by:
		comment += "\n^(Last edited by: /u/" + edited_by + ")\n"

	comment += (
		"\n^(Version " + __version__ + ") ^| " +
		"[^contact](http://www.reddit.com/message/compose/?to=xoru) ^| " +
		"[^(bot info)](http://redd.it/30srzq/) ^| " +
		"[^source](http://github.com/xoru/CSGO_Bot) ^| " +
		"[^(CSGO_Bot major update!)](http://redd.it/3bnvld)"
	)
	return comment

def create_poll(teams):
	"""Creates a strawpoll.

	Args:
		teams (list): A list of team names.
	Returns:
		If successful, a string with the URL of the newly created strawpoll, False
		otherwise.
	"""
	if len(teams) < 2:
		return False
	data = {
		'title': 'Who will win?',
		'options': teams,
		'permissive': True
	}
	r = requests.post('http://strawpoll.me/api/v2/polls', data)
	if 'id' in r.json():
		# Return the URL of the newly created poll
		return "http://strawpoll.me/" + str(r.json()['id'])
	return False

def main():
	"""CSGO_Bot's main function. This script is called every 5 minutes through cron.

	"""
	oauth = configparser.ConfigParser()
	oauth.read(__location__ + 'oauth.ini')

	players = get_yaml("players")
	teams = get_yaml("teams")
	bot.log("Players and teams loaded.")

	# Connect to reddit with praw, set oauth info.
	r = praw.Reddit("CSGO Competitive Stats Bot v" + __version__,
		oauth_client_id = oauth['OAuth']['client_id'],
		oauth_client_secret = oauth['OAuth']['client_secret'],
		oauth_redirect_uri = oauth['OAuth']['redirect_uri']
	)

	# OAuth access information. https://github.com/xoru/easy-oauth
	access_information = {
		'access_token': oauth['OAuth']['access_token'],
		'refresh_token': oauth['OAuth']['refresh_token'],
		'scope': oauth['Scope']
	}

	# Update access_token with our permanent refresh_token.
	access_information = r.refresh_access_information(access_information['refresh_token'])

	r.set_access_credentials(**access_information)


	# Load posts, comments, and messages
	posts = r.get_subreddit(subreddit).get_new(limit = 20)
	comments = r.get_comments(subreddit, limit = 100)
	messages = r.get_messages(limit = 15)

	bot.log("Looking at messages")
	for message in messages:
		if not file_string_exists('messages.txt', message.id): # If we haven't already dealt with this message
			if message.subject == "COMMAND: No PM":
				file_string_append('nopm.txt', message.author.name)
				r.send_message(message.author.name, "Command successful", "You will no longer receive edit confirmation messages.\n\n---\n^(This was an automated message. Regret your decision already? Click) ^[here](http://www.reddit.com/message/compose/?to=CSGO_Bot&subject=COMMAND:%20PM&message=Do%20not%20change%20the%20subject%20text,%20just%20click%20send.) ^(to turn edit confirmation messages back on again.)")
				bot.log("Added " + message.author.name + " to nopm.txt")
			elif message.subject == "COMMAND: PM":
				file_string_remove('nopm.txt', message.author.name)
				r.send_message(message.author.name, "Command successful", "You will now receive edit confirmation messages.\n\n---\n^(This was an automated message. Regret your decision already? Click) ^[here](http://www.reddit.com/message/compose/?to=CSGO_Bot&subject=COMMAND:%20No%20PM&message=Do%20not%20change%20the%20subject%20text,%20just%20click%20send.) ^(to turn edit confirmation messages back off again.)")
				bot.log("Deleted " + message.author.name + " from nopm.txt")
			file_string_append('messages.txt', message.id) # Mark message as done.

	bot.log("Looking at posts")
	for post in posts:
		if (post.link_flair_text == "Match" or post.link_flair_text == "Match has started") and "|" in post.title:
			if not file_string_exists("posts.txt", post.id):
				found_teams = find_teams(post.title, teams, False)
				found_players = find_players(post.selftext, players)

				poll_teams = [teams[team]['names'][0] for team in found_teams]
				strawpoll = create_poll(poll_teams)
				reply = construct_comment(found_teams, found_players, teams, players, strawpoll, True)

				# Add comment to thread
				added_comment = post.add_comment(reply)
				bot.log("Added comment to " + post.id)

				# Store post id
				file_string_append("posts.txt", post.id)

				# Add reply information
				replies = get_yaml("replies")
				replies.update({added_comment.id: {
					'players':   found_players,
					'teams':     found_teams,
					'strawpoll': strawpoll
				}})
				set_yaml("replies", replies)

	bot.log("Looking at comments")
	for comment in comments:
		if not file_string_exists("comments.txt", comment.id):
			# Skip comment if it doesn't mention us, or if ignore command is used.
			if "u/csgo_bot" not in comment.body.lower() or "+ignore" in comment.body.lower():
				continue

			# Skip comment if it is deleted.
			if comment.body == None or comment.author == None:
				continue

			# Let's not reply to ourselves or ignored users.
			if comment.author.name == "CSGO_Bot" or file_string_exists("ignored.txt", comment.author.name):
				continue

			# Skip comments that have both remove and add commands.
			if ("+p" in comment.body.lower() and "-p" in comment.body.lower()) or ("+t" in comment.body.lower() and "-t" in comment.body.lower()):
				continue

			case_sensitivity = False
			remove_players = False
			remove_teams = False
			found_players = []
			found_teams = []
			activated_commands = []

			if "+case" in comment.body.lower():
				case_sensitivity = True
				activated_commands.append("+case")

			# Both +p and -p have to use the find_players function to detect players, so let's deal with them both here.
			if "+p" in comment.body.lower() or "-p" in comment.body.lower():
				found_players = find_players(comment.body, players, case_sensitivity)

				if "-p" in comment.body.lower():
					# Mark the players we just found as ones we want to remove.
					remove_players = True
					activated_commands.append("-p")
				else:
					activated_commands.append("+p")

			if "+t" in comment.body.lower() or "-t" in comment.body.lower():
				found_teams = find_teams(comment.body, teams, False)

				if "-t" in comment.body.lower():
					remove_teams = True
					activated_commands.append("-t")
				else:
					activated_commands.append("+t")

			if found_players or found_teams:
				if "+reply" not in comment.body.lower() and comment.is_root == False:
					parent = r.get_info(thing_id=comment.parent_id)
					if parent.author and parent.author.name == "CSGO_Bot":

						replies = get_yaml("replies")
						parent_players = replies[parent.id]['players']
						parent_teams = replies[parent.id]['teams']
						strawpoll = replies[parent.id]['strawpoll']
						final_players = None
						final_teams = None
						player_difference = False
						team_difference = False

						if found_players:
							if remove_players:
								final_players = [player for player in parent_players if player not in found_players]
							else:
								# Merge lists together (No duplicates)
								final_players = list(set(parent_players) | set(found_players))

							if parent_players != final_players:
								player_difference = True
						else:
							final_players = parent_players

						if found_teams:
							if remove_teams:
								final_teams = [team for team in parent_teams if team not in found_teams]
							else:
								final_teams = list(set(parent_teams) | set(found_teams))

							# Check if we need to create a new strawpoll
							if parent_teams != final_teams:
								parent_teams = final_teams
								team_difference = True
								poll_teams = [teams[team]['names'][0] for team in final_teams]
								strawpoll = create_poll(poll_teams)
						else:
							final_teams = parent_teams

						# Only edit the comment if there is a difference between the old and new one.
						if player_difference or team_difference:
							reply = construct_comment(final_teams, final_players, teams, players, strawpoll, True, comment.author.name)

							# Edit the parent comment with the new information.
							parent.edit(reply)
							bot.log("Edited " + parent.id + " from " + comment.id + " (" + comment.author.name + ")")

							file_string_append("comments.txt", comment.id)

							# Update reply information.
							replies = get_yaml("replies")
							replies.update({parent.id: {
								'players':   final_players,
								'teams':     final_teams,
								'strawpoll': strawpoll
							}})
							set_yaml("replies", replies)

							# If the commenter wants to recieve edit-PMs
							if not file_string_exists('nopm.txt', comment.author.name):
								message = "[Link](" + parent.permalink + ")\n\nActivated commands: " + ", ".join(activated_commands) + "\n\n"

								if player_difference:
									message += "Players detected: "

									# Find out which players are added/removed
									if remove_players:
										affected_players = found_players
									else:
										affected_players = [player for player in found_players if player not in parent_players]

									bot.log("New players: " + str(affected_players))
									message += ", ".join("[" + players[player] + "](http://www.hltv.org/?pageid=173&playerid=" + str(player) + ")" for player in affected_players) + "\n\n"

								if team_difference:
									message += "Teams detected: "

									# Find out which teams are added/removed
									if remove_teams:
										affected_teams = found_teams
									else:
										affected_teams = [team for team in found_teams if team not in parent_teams]

									bot.log("Found teams: " + str(affected_teams))
									message += ", ".join("[" + teams[team]['names'][0] + "](http://www.hltv.org/?pageid=179&teamid=" + team + ")" for team in affected_teams) + "\n\n"


								message += "---\n^(This was an automated message. If you don't want to receive confirmation on summoning, click) ^[here](http://www.reddit.com/message/compose/?to=CSGO_Bot&subject=COMMAND:%20No%20PM&message=Do%20not%20change%20the%20subject%20text,%20just%20click%20send.)."
								r.send_message(comment.author.name, "Edit successful", message)
								bot.log("Sent confirmation message to " + comment.author.name)

				else:
					poll_teams = [teams[team]['names'][0] for team in found_teams]
					strawpoll = create_poll(poll_teams)

					# Don't make strawpolls for comment replies
					reply = construct_comment(found_teams, found_players, teams, players, None, False, comment.author.name)
					added_comment = comment.reply(reply)

					replies = get_yaml("replies")
					replies.update({added_comment.id: {
						'players':   found_players,
						'teams':     found_teams
					}})
					set_yaml("replies", replies)

if __name__ == "__main__":
	try:
		main()
		bot.log("Done!")
		sys.exit(1)
	except KeyboardInterrupt:
		bot.log("Forcefully quit.")
		sys.exit(1)