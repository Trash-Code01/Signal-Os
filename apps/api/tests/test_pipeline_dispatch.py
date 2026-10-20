"""Dispatch must distinguish queue acceptance from a running consumer."""
from unittest.mock import Mock
import time

import pytest
from fastapi import HTTPException
import main
import worker
from core.models import Business, Campaign, JobRun, Opportunity, Website
from test_accounts_and_contact_options import setup, headers


@pytest.mark.parametrize('queues', [None, {}, {'worker': [{'name': 'another_queue'}]}])
def test_production_dispatch_rejects_missing_queue_consumer(monkeypatch, queues):
    monkeypatch.setattr(main, 'IS_STAGING', False)
    inspector = Mock()
    inspector.active_queues.return_value = queues
    monkeypatch.setattr(worker.celery_app.control, 'inspect', Mock(return_value=inspector))
    task = Mock()
    with pytest.raises(HTTPException) as exc:
        main._dispatch_task(task, 12)
    assert exc.value.status_code == 503
    task.apply_async.assert_not_called()
    task.assert_not_called()


def test_production_dispatch_publishes_to_verified_queue_without_retry(monkeypatch):
    monkeypatch.setattr(main, 'IS_STAGING', False)
    inspector = Mock()
    inspector.active_queues.return_value = {'worker': [{'name': 'devacia_queue'}]}
    monkeypatch.setattr(worker.celery_app.control, 'inspect', Mock(return_value=inspector))
    task = Mock()
    assert main._dispatch_task(task, 12) is task.apply_async.return_value
    task.apply_async.assert_called_once_with(args=[12], kwargs={}, queue='devacia_queue', retry=False)


def test_broker_failure_does_not_launch_untracked_production_thread(monkeypatch):
    monkeypatch.setattr(main, 'IS_STAGING', False)
    monkeypatch.setattr(worker.celery_app.control, 'inspect', Mock(side_effect=ConnectionError('broker down')))
    task = Mock()
    with pytest.raises(HTTPException) as exc:
        main._dispatch_task(task, 12)
    assert exc.value.status_code == 503
    task.assert_not_called()


def test_campaign_progress_counts_businesses_once_after_research_retry(setup):
    client, factory = setup
    with factory() as db:
        db.info['owner_id'] = 1
        campaign = Campaign(name='Retried research', target_quantity=1, status='completed')
        db.add(campaign)
        db.flush()
        business = Business(name='Retried business', campaign_id=campaign.id, status='qualified')
        db.add(business)
        db.flush()
        for _ in range(2):
            db.add(Website(business_id=business.id, url='https://example.com'))
            db.add(Opportunity(business_id=business.id))
        db.commit()
        cid = campaign.id
    response = client.get(f'/api/campaigns/{cid}/status', headers=headers(1))
    assert response.status_code == 200
    stages = {stage['key']: stage for stage in response.json()['stages']}
    for key in ['crawler', 'ai_sdr']:
        assert stages[key]['count'] == stages[key]['total'] == 1


def test_failed_campaign_dispatch_is_terminal_and_resumable(setup, monkeypatch):
    client, factory = setup
    def unavailable(*args, **kwargs):
        raise HTTPException(503, 'Campaign worker is unavailable. Retry after it restarts.')
    monkeypatch.setattr(main, '_dispatch_task', unavailable)
    response = client.post('/api/campaigns', headers=headers(1), json={
        'name':'Worker outage', 'country':'India', 'cities':['Pune'], 'industry':'tailor',
        'target_quantity':1, 'min_quality_score':60,
    })
    assert response.status_code == 503
    with factory() as db:
        db.info['owner_id'] = 1
        campaign = db.query(Campaign).one()
        cid = campaign.id
        assert campaign.status == 'failed'
        assert db.query(JobRun).one().error_message == 'Campaign worker is unavailable. Retry after it restarts.'
    response = client.post(f'/api/campaigns/{cid}/resume', headers=headers(1))
    assert response.status_code == 503  # Retryable worker error, not an already-running conflict.
    status = client.get(f'/api/campaigns/{cid}/status', headers=headers(1)).json()
    assert status['terminal'] and status['status'] == 'failed'
    assert 'worker is unavailable' in status['summary']


def test_real_celery_consumer_delivers_campaign_through_http(setup, monkeypatch):
    """Exercise real queue serialization and consumption using isolated memory transport."""
    from celery.contrib.testing.worker import start_worker
    client, _ = setup
    monkeypatch.setattr(main, 'IS_STAGING', False)
    monkeypatch.setattr(worker.celery_app.conf, 'task_always_eager', False)
    with start_worker(worker.celery_app, pool='threads', concurrency=1,
                      queues=['devacia_queue'], perform_ping_check=False, shutdown_timeout=15):
        response = client.post('/api/campaigns', headers=headers(1), json={
            'name':'Real queue QA', 'country':'India', 'cities':['Pune'], 'industry':'tailor',
            'target_quantity':1, 'min_quality_score':60,
        })
        assert response.status_code == 200, response.text
        cid = response.json()['campaign_id']
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            status = client.get(f'/api/campaigns/{cid}/status', headers=headers(1)).json()
            if status['terminal']:
                break
            time.sleep(0.1)
        assert status['status'] == 'completed', status
        assert status['stats']['qualified'] == 1
        assert client.get(f'/api/crm/leads?campaign_id={cid}', headers=headers(1)).json()['total'] == 1
