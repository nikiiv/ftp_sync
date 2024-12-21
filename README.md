A simple utiity to sync a remote ftp server with a local one
The config.ini can define multuple server, each in their own section
The sync will skip files with the same name and size and will generate a report for all new files on the remote and all files on the local that aren't on remote.
Another twist is that if you configute a dry run in the config file or pass -dry as a parameter, it will just check for new files and store the report in the output_path
Confifg file is self explanatory

To use
1. Clone the project
2. cd into it
3. create a virtual environnment `python -m venv venv`
4. Activate it by source venv/bin/activate
5. Load requirements `pip install -r requirements.txt`
6. Modify config.ini to suit your needs. You can optionally pass a different config file by `-c` or `--conf` parameter
7. When executing it you can specify different ftp server using `-f` or `--ftp`. The default server config section is ftp
8. The `-dry` otion will override what is in the config file
9. Sample python3 `ftp_sync.py -f ftp -c config.ini -dry`
10. Profit

Comments are welcome. This is my first python project, I am mostly Java and Elixir guy..
Specially how can I imporve the distribution and the ease of use
