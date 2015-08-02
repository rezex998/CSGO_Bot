# Please configure paths before running.

printf "Running CSGO_Bot update (CTRL-C to exit)\n========================================\n"
sleep 2

# Pause cronjob by adding a comment to the start of all lines.
printf "> Pausing cron job...\n"
sudo sed -i 's/^/# /' /path/to/cronjob

# Run the update python script.
printf "> Running update.py...\n"
/usr/local/bin/python /path/to/update.py

# Resume cronjob by removing the comments.
printf "> Resuming cron job...\n"
sudo sed -i 's/^# //' /path/to/cronjob

# That's it!
printf "> Update complete.\n"
