.PRECIOUS: users_github.txt
users_github.txt:
	python github.py users_github.txt

users_stack.txt: Users.xml
	sed -f stackoverflow.sed stackoverflow_users.txt

users_github_sorted.txt: users_github.txt
	sort users_github.txt > users_github_sorted.txt

users_stack_sorted.txt: users_stack.txt
	sort users_stack.txt > users_stack_sorted.txt

users_common.txt: users_stack_sorted.txt users_github_sorted.txt
	comm -12 users_stack_sorted.txt users_github_sorted.txt > users_common.txt
