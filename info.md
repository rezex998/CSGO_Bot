Current version: 1.3-beta

---
###Introduction
/u/CSGO_Bot is a reddit bot that provides statistics about professional CS:GO players and teams. It is written in Python and uses PRAW. It only runs in the /r/csgobetting subreddit.

###Features
- Detects team names (and common abbreviations) in submission title with match flair.
- Detects player names in submission body.
- Displays statistics on detected teams and players in easy-to-read tables.
- Creates strawpoll between detected teams.
- Multiple commands.
- Displays statistics about past matchups.
- Can automatically edit own comments to add/remove players and teams.

###Summoning
To summon the bot, your comment must include "/u/CSGO_Bot" and at least one of the following commands:

Command|Description|Usage|Example
:-:|:-:|:-:|:-:
+p|*Add player* command.|Reply to /u/CSGO_Bot, include the command and at least one player name in your comment.|/u/CSGO_Bot +p allu, flusha
-p|*Remove player* command.|---|/u/CSGO_Bot +case -p adreN
+t|*Add team* command.|Reply to /u/CSGO_Bot, include the command and at least one team name in your comment.|/u/CSGO_Bot +t TSM and Fnatic
-t|*Remove team* command.|---|/u/CSGO_Bot -t NiP
+ignore|*Ignore comment* command.|Include the command in your comment.|/u/CSGO_Bot is a robot! It doesn't have feelings! +ignore
+case|*Case sensitive players* command.|---|/u/CSGO_Bot +case +p AdreN
+reply|*Force reply* command.|---|/u/CSGO_Bot +reply +p +t +case adreN, s1mple, TSM, C9

Note: You can not use +p and -p (nor +t and -t) in the same comment.

###Planned features
~~Striked out text~~ = implemented in the latest version.

- Use strawpoll of main post if found.

###Caveats
None known

---

Suggestions and feedback are welcome.

Enjoy!