# Sniff

Just having some fun with agents, and getting better at python :)

Currently limited to the included 'toy-webserver.zip' file for testing.
The idea is: give it a .zip file (or directory), and it extracts everything into a sandboxed docker container, then routes all AI model commands through that isolated environment. This way the agent can poke around and run commands without potentially messing up your actual system.

## Running the project

Little clunky, need to have a way to actually install it later
but for now this works:

1. Install docker
2. Install uv
3. uv run sniffer
