setup:
	git init --bare jobe.git
	cp jobe.py jobe.git/hooks/post-receive
	chmod +x jobe.git/hooks/post-receive
	git clone jobe.git tmpclient
	cd tmpclient && touch jobeinit && git add jobeinit && git commit -a -m "Initial commit" && git push && cd .. && rm -rf tmpclient
	@echo "JOBE has been setup, pull from the jobe.git repository to begin"

clean:
	rm -rf tmpclient jobe.git