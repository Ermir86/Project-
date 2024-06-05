
clean:
	@rm -rf server/.pio server/.vscode client/__pycache__

client: 
	@python3 client/client.py 

server:
	@cd server && pio run -t upload 

.PHONY: clean client server 
