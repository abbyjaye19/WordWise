"""Back-end services (AI agents, tutor search, user storage).

Planned modules — added in later phases:
  ai.py        gpt-6-luna calls via Portkey, with token logging to output/
  tutors.py    search over data/sample/tutors.json
  resources.py curated resource hub content
  users.py     user accounts and saved preferences
Pages should call these services rather than talking to the model directly.
"""
