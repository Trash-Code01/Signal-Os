import asyncio
import aiohttp
import base64
import os

async def test():
    username = os.environ.get('DATAFORSEO_USERNAME')
    password = os.environ.get('DATAFORSEO_PASSWORD')
    credentials = f'{username}:{password}'
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    headers = {'Authorization': f'Basic {encoded_credentials}', 'Content-Type': 'application/json'}
    payload = [{'keyword': 'Roofing in Dallas, TX', 'language_code': 'en', 'location_code': 2840, 'depth': 100}]
    
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.dataforseo.com/v3/serp/google/maps/live/advanced', headers=headers, json=payload) as resp:
            data = await resp.json()
            tasks = data.get('tasks', [{}])
            status = tasks[0].get('status_code')
            print(f'Status: {status}')
            items = tasks[0].get('result', [{}])[0].get('items', [])
            print(f'Got {len(items)} items')

asyncio.run(test())
