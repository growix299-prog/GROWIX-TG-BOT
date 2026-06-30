import os
from supabase import create_client

def load_env():
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        os.environ[k] = v.strip('"\'')
    except Exception as e:
        print("Error loading .env", e)

load_env()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    try:
        with open('backend/.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        os.environ[k] = v.strip('"\'')
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
    except:
        pass

if not supabase_url or not supabase_key:
    print("No Supabase credentials found.")
    exit(1)

db = create_client(supabase_url, supabase_key)

products = [
    {'name': 'Netflix', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'YouTube', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'Spotify', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'Amazon Prime', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'Disney+ Hotstar', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'Steam', 'category': 'Games', 'price': 199.0, 'active': True},
    {'name': 'Zee5', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'Sony Liv', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'ChatGPT', 'category': 'AI', 'price': 199.0, 'active': True},
    {'name': 'CapCut', 'category': 'VideoEditing', 'price': 199.0, 'active': True},
    {'name': 'Google One', 'category': 'AI', 'price': 99.0, 'active': True},
    {'name': 'Canva', 'category': 'VideoEditing', 'price': 99.0, 'active': True},
    {'name': 'Crunchyroll', 'category': 'OTT', 'price': 99.0, 'active': True},
    {'name': 'Claude AI', 'category': 'AI', 'price': 199.0, 'active': True},
    {'name': 'Adobe Creative Cloud', 'category': 'VideoEditing', 'price': 499.0, 'active': True},
    {'name': 'Picsart', 'category': 'VideoEditing', 'price': 0, 'active': True}
]

for p in products:
    try:
        existing = db.table('products').select('*').eq('name', p['name']).execute()
        if not existing.data:
            db.table('products').insert(p).execute()
            print(f"Inserted: {p['name']}")
        else:
            print(f"Skipped (already exists): {p['name']}")
    except Exception as e:
        print(f"Error inserting {p['name']}: {e}")
