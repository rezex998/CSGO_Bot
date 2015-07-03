import os
import re
import yaml
import json
import praw
import requests
import datetime

from lxml import html
from operator import itemgetter
from bot import username, password

subreddit = "csgobetting"
__version__ = "1.0-beta"
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + '/'


def file_string_exists(filename, string):
	"""Checks if string exists in file (line by line search)."""
	with open(__location__ + filename) as f:
		for l in f:
			l = l.rstrip().lower()
			if l == string.lower():
				return True
	return False

def file_string_append(filename, string):
	"""Appends string to end of file."""
	with open(__location__ + filename, 'a') as f:
		f.write(string + '\n')

def file_string_remove(filename, string):
	"""Removes string from file."""
	lines = None
	with open(__location__ + filename) as f:
		lines = f.readlines()
	with open(__location__ + filename, 'w') as f:
		for line in lines:
			if line != string + '\n':
				f.write(line)

def get_yaml(filename):
	"""Gets the content of a YAML file."""
	with open(__location__ + filename + ".yaml") as f:
		file = yaml.load(f)
	if not file:
		return []
	return file

def set_yaml(filename, data):
	"""Dumps data to a YAML file."""
	with open(__location__ + filename + ".yaml", "w") as f:
		yaml.dump(data, f, default_flow_style=False)

def add_csgonuts():
	"""
	Adds 'csgonuts' key to teams that are in csgonuts.txt.

	csgonuts.txt is filled with a simple web-scraper.
	The value is the team's name on csgonuts, as decided in csgonuts.txt
	"""
	teams = get_yaml('teams')
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
	"""Updates teams and stores them in teams.yaml. Fetches data from HLTV.org."""
	# TODO: Update this old function. (and update_players())
	invalid = 0
	while invalid < 50:
		id += 1
		page = requests.get("http://www.hltv.org/?pageid=179&teamid=" + str(id))
		tree = html.fromstring(page.text)
		name = tree.xpath('(//div[contains(., "Team stats: ") and @class="tab_content"])[1]/text()')[0].replace("Team stats: ", "").strip()
		maps = tree.xpath('(//div[@style="font-weight:normal;width:180px;float:left;color:black;text-align:right;"])[1]/text()')[0]

		if str(name) == "No team" or str(name) == "Key stats":
			invalid += 1
			bot.log("No team found")
			continue

		invalid = 0
		page = requests.get("http://www.hltv.org/?pageid=188&teamid=" + str(id))
		tree = html.fromstring(page.text)

		try:
			latest_match = tree.xpath('(//*[@id="back"]/div[12]/div[3]/div[2]/div[3]/div/div[6]/div/a[1]/div)/text()')[0]
		except IndexError:
			latest_match = tree.xpath('(//*[@id="back"]/div[10]/div[3]/div[2]/div[3]/div/div[6]/div/a[1]/div)/text()')[0]

		# Check if team has played at least one match in 2014 or later.
		if int(maps) > 0 and int(latest_match.split()[1]) >= 14:
			teams = get_yaml("teams")
			teams.update({id: {"names": [str(name)]}})
			set_yaml("teams", teams)

def update_players(id = 0):
	"""Updates players and stores them in players.yaml. Fetches data from HLTV.org."""
	invalid = 0
	while invalid < 50:
		id += 1

		page = requests.get("http://www.hltv.org/?pageid=173&playerid=" + str(id)) # Overview page
		tree = html.fromstring(page.text)
		name = tree.xpath('(//div[@class="covSmallHeadline" and @style="width:100%;float:left;"])[1]/text()')[0]
		maps = tree.xpath('(//div[@class="covSmallHeadline" and @style="font-weight:normal;width:100px;float:left;text-align:right;color:black"])[5]/text()')[0]

		if str(name) == "N/A" or str(name) == "Key stats":
			invalid += 1
			continue

		invalid = 0
		page = requests.get("http://www.hltv.org/?pageid=246&playerid=" + str(id)) # Match history page
		tree = html.fromstring(page.text)

		try:
			latest_match = tree.xpath('(//*[@id="back"]/div[12]/div[3]/div[2]/div[2]/div[2]/div/div[6]/div/div[1]/a)/text()')[0]
		except IndexError:
			latest_match = tree.xpath('(//*[@id="back"]/div[10]/div[3]/div[2]/div[2]/div[2]/div/div[6]/div/div[1]/a)/text()')[0]

		if not latest_match:
			continue

		# Check if player has played at least one match in 2014 or later
		if int(maps) > 0 and int(latest_match.split()[1]) >= 14:
			players = get_yaml("players")
			players.update({id: {"name": str(name)}})
			set_yaml("players", players)

def find_teams(text, teams, case_sensitive = False):
	"""
	Searches for team names and abbreviations in a text.
	Team list needs to be provided in the teams variable (from get_teams() function).
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
	"""
	Searches for player names in a text.
	Player list needs to be provided in the players variable (from get_players() function).
	"""
	if text is None:
		return None

	if not case_sensitive:
		text = text.lower()

	found_players = []
	text = text.replace(",", " ").replace(".", " ").replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")

	for player in players:
		name = players[player]['name']
		if not case_sensitive:
			name = name.lower()

		if name in text.split() or (" " in name and name in text):
			found_players.append(player)
	return found_players

def get_player_stats(found_players, players):
	"""Gets player statistics from HLTV."""
	player_stats = []
	for player in found_players:
		url = "http://www.hltv.org/?pageid=173&playerid=" + str(player) # Overview page
		page = requests.get(url)
		tree = html.fromstring(page.text)

		# The main div index on HLTV changes frequently between 10 and 12.
		main_div = 12

		# Find out which main div index is being used.
		try:
			tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[2]/div[2]/div[9]/div/div[2]/a)/text()')[0]
		except IndexError:
			main_div = 10

		# Web scraping is a dirty... dirty... job...
		team            = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[2]/div[2]/div[9]/div/div[2]/a)/text()')[0]
		rating          = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[21]/div/div[2])/text()')[0]
		total_kills     = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[3]/div/div[2])/text()')[0]
		total_deaths    = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[7]/div/div[2])/text()')[0]
		kd_ratio        = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[9]/div/div[2])/text()')[0]
		kills_per_round = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[15]/div/div[2])/text()')[0]

		stats = {
			'name':            players[player]['name'],
			'url':             url,
			'team':            team,
			'team_url':        "http://www.hltv.org" + tree.xpath('(//a[text()="' + team + '"]/@href)')[0],
			'rating':          rating,
			'total_kills':     total_kills,
			'total_deaths':    total_deaths,
			'kd_ratio':        kd_ratio,
			'kills_per_round': kills_per_round
		}
		player_stats.append(stats)
	player_stats = sorted(player_stats, key=itemgetter('rating'), reverse=True) # Sort by rating by default
	return player_stats

def get_team_stats(found_teams, teams):
	"""Gets team statistics from HLTV."""
	team_stats = []
	for team in found_teams:
		url = "http://www.hltv.org/?pageid=179&teamid=" + str(team) # Overview page
		page = requests.get(url)
		tree = html.fromstring(page.text)
		main_div = 12

		try:
			tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[5]/div/div[2])/text()')[0]
		except IndexError:
			main_div = 10

		wdl         = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[5]/div/div[2])/text()')[0].replace(" ", "").split("/")
		maps_played = tree.xpath('(//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div[2]/div[3]/div/div[2])/text()')[0]
		total_played = int(wdl[0]) + int(wdl[2])
		win_percentage = str(round((int(wdl[0]) / total_played) * 100)) + "%"

		stats = {
			'name':              teams[team]['names'][0],
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
				match_link = tree.xpath('//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div/div[' + str(i) + ']/div/a[1]/@href')

				match_team1 = tree.xpath('//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div/div[' + str(i) + ']/div/a[2]/div/text()')[0]
				match_team1 = match_team1[match_team1.index("(") + 1:match_team1.rindex(")")] # Get text inside parentheses

				match_team2 = tree.xpath('//*[@id="back"]/div[' + str(main_div) + ']/div[3]/div[2]/div[3]/div/div[' + str(i) + ']/div/a[3]/div/text()')[0]
				match_team2 = match_team2[match_team2.index("(") + 1:match_team2.rindex(")")]

				match = {
					'url':  "http://www.hltv.org" + match_link[0],
					'team1': match_team1,
					'team2': match_team2
				}

				stats['recent_matches'].append(match)
			except IndexError:
				break
		team_stats.append(stats)
	team_stats = sorted(team_stats, key=itemgetter('maps_played'), reverse=True) # Sort by maps_played by default
	return team_stats

def get_matchup(team1, team2):
	"""Gets matchup statistics between two teams from CSGOnuts."""
	if not team1 or not team2 or ('csgonuts' not in team1 or 'csgonuts' not in team2):
		return None

	page = requests.get("http://www.csgonuts.com/history?t1=" + team1['csgonuts'] + "&t2=" + team2['csgonuts'])
	tree = html.fromstring(page.text)
	error_message = tree.xpath('(/html/body/div/div[2]/div[1]/div[2]/div)/text()')[0]

	if 'We have no record of match between' in error_message:
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
	"""Magically put everything together into markdown."""
	if found_teams is None and found_players is None:
		return None

	comment = ""

	if found_players is not None:
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

	if found_teams is not None:
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

	matchup_team1 = None
	matchup_team2 = None
	for team in found_teams:
		if matchup_team1 and matchup_team2:
			break
		if matchup_team1 is None:
			matchup_team1 = all_teams[team]
		else:
			matchup_team2 = all_teams[team]

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
		if (player_stats is None) or (len(player_stats) < 10) or (team_stats is None) or (len(team_stats) < 2):
			comment += "\n^(Missing players/teams detected. This could be due to there not being any information on them on HLTV.)\n"

	comment += "\n^(**Note:** Adding irrelevant players or teams will result in being added to the bot ignore list without warning.)\n"

	if edited_by is not None:
		comment += "\n^(Last edited by: /u/" + edited_by + ")\n"

	comment += (
		"\n^(Version + " + __version__ + ") ^| " +
		"[^contact](http://www.reddit.com/message/compose/?to=xoru) ^| " +
		"[^(bot info)](http://redd.it/30srzq/) ^| " +
		"[^source](http://github.com/xoru/CSGO_Bot) ^| " +
		"[^(CSGO_Bot major update!)](http://redd.it/3bnvld)"
	)
	return comment

def create_poll(teams):
	"""Creates a strawpoll."""
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
	try:
		players = get_yaml("players")
		teams = get_yaml("teams")
		bot.log("Players and teams loaded.")

		# Connect to reddit with praw
		r = praw.Reddit("CSGO Competitive Stats Bot v" + __version__)
		r.login(username(), password())

		# Load posts, comments, and messages
		posts = r.get_subreddit(subreddit).get_new(limit = 20)
		comments = []
		messages = r.get_messages(limit = 15)

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

		for post in posts:
			if (post.link_flair_text == "Match" or post.link_flair_text == "Match has started") and "|" in post.title:
				comments.extend(praw.helpers.flatten_tree(post.comments))

				if not file_string_exists("posts.txt", post.id):
					found_teams = find_teams(post.title, teams, False)
					found_players = find_players(post.selftext, players, True)

					poll_teams = [teams[team]['names'][0] for team in found_teams]
					strawpoll = create_poll(poll_teams)
					reply = construct_comment(found_teams, found_players, teams, players, strawpoll, True)

					# Add a comment
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
						if parent.author.name == "CSGO_Bot":

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

										# Find out which players added are new ones
										new_players = [player for player in found_players if player not in parent_players]
										bot.log(str(found_players))
										message += ", ".join("[" + found_players[player]['name'] + "](http://www.hltv.org/?pageid=173&playerid=" + player + ")" for player in new_players) + "\n\n"

									if team_difference:
										message += "Teams detected: "
										new_teams = [team for team in found_teams if team not in parent_teams]
										message += ", ".join("[" + found_teams[team]['names'][0] + "](http://www.hltv.org/?pageid=179&teamid=" + team + ")" for team in new_teams) + "\n\n"

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
	except KeyboardInterrupt:
		bot.log("\nForcefully quit.")

main()
