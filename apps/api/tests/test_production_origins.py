"""Cookie-authenticated campaign submissions through the hosted frontends."""
import pytest
from test_accounts_and_contact_options import setup, headers


@pytest.mark.parametrize('origin', [
    'https://signaldevos.netlify.app',
    'https://devacia-frontend.onrender.com',
])
def test_hosted_frontend_cookie_can_create_campaign(setup, origin):
    client, _ = setup
    client.cookies.set('access_token', headers(1)['Authorization'][7:])
    response = client.post('/api/campaigns', headers={'Origin': origin}, json={
        'name': 'Hosted origin QA', 'country': 'India', 'cities': ['Pune'],
        'industry': 'tailor', 'target_quantity': 1, 'min_quality_score': 0,
        'website_filter': 'no_website', 'discovery_channels': ['google_maps'],
    })
    assert response.status_code == 200, response.text
    cid = response.json()['campaign_id']
    status = client.get(f'/api/campaigns/{cid}/status').json()
    assert status['status'] == 'completed'
    assert status['stats']['qualified'] == 1
    assert all(stage['key'] != 'crawler' for stage in status['stages'])


@pytest.mark.parametrize('origin', [
    'https://unrelated.netlify.app',
    'https://signaldevos.netlify.app.attacker.example',
    'http://signaldevos.netlify.app',
    '',
])
def test_cookie_campaign_rejects_unapproved_origins(setup, origin):
    client, _ = setup
    client.cookies.set('access_token', headers(1)['Authorization'][7:])
    response = client.post('/api/campaigns', headers={'Origin': origin}, json={
        'name': 'Must not create', 'country': 'India', 'cities': ['Pune'],
        'industry': 'tailor', 'target_quantity': 1,
    })
    assert response.status_code == 403
    assert response.json()['detail'] == 'Invalid request origin'
    assert client.get('/api/campaigns').json() == []


def test_netlify_preflight_is_allowed(setup):
    client, _ = setup
    response = client.options('/api/campaigns', headers={
        'Origin': 'https://signaldevos.netlify.app',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'https://signaldevos.netlify.app'
    assert response.headers['access-control-allow-credentials'] == 'true'
