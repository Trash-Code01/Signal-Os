with open('apps/api/core/database.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('raw_url.replace("postgres://", "postgresql://", 1)', 'raw_url.replace("postgres://", "postgresql+psycopg://", 1)')
# Also catch cases where it might already be postgresql:// (from local .env or defaults)
text = text.replace('DATABASE_URL = raw_url', 'if raw_url.startswith("postgresql://"):\n    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)\nDATABASE_URL = raw_url')

with open('apps/api/core/database.py', 'w', encoding='utf-8') as f:
    f.write(text)