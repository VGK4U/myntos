import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from sqlalchemy import text


class TestWhatsAppClusterCoordinator(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        db = SessionLocal()
        # Clean test rows
        db.execute(text("DELETE FROM whatsapp_bot_queue WHERE instance_id LIKE 'test-%'"))
        db.execute(text("DELETE FROM whatsapp_bot_lease WHERE id = 1"))
        db.commit()
        db.close()

    def tearDown(self):
        db = SessionLocal()
        db.execute(text("DELETE FROM whatsapp_bot_queue WHERE instance_id LIKE 'test-%'"))
        db.commit()
        db.close()

    def test_leader_election_and_follower_replication(self):
        # 1. Instance 1 heartbeats - should become leader
        res1 = self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-1',
            'instance_host': '172.31.0.10',
            'status': 'qr_ready',
            'qr_data': '2@test-qr-data-abc',
            'qr_url': 'https://api.qrserver.com/test-qr-1',
            'can_send_now': False,
            'generation_id': 1
        })
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['is_leader'])
        self.assertEqual(data1['leader_id'], 'test-node-1')

        # 2. Instance 2 heartbeats - should be rejected as leader, returned as follower
        res2 = self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-2',
            'instance_host': '172.31.0.11'
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertFalse(data2['is_leader'])
        self.assertEqual(data2['leader_id'], 'test-node-1')
        self.assertEqual(data2['leader_state']['status'], 'qr_ready')
        self.assertEqual(data2['leader_state']['qr_data'], '2@test-qr-data-abc')
        self.assertEqual(data2['leader_state']['qr_url'], 'https://api.qrserver.com/test-qr-1')

        # 3. Instance 3 heartbeats - should also receive Instance 1's QR code
        res3 = self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-3',
            'instance_host': '172.31.0.12'
        })
        self.assertEqual(res3.status_code, 200)
        data3 = res3.json()
        self.assertFalse(data3['is_leader'])
        self.assertEqual(data3['leader_state']['qr_data'], '2@test-qr-data-abc')

        # 4. Instance 1 connects (QR scanned) - updates status to connected
        res1_conn = self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-1',
            'status': 'connected',
            'can_send_now': True,
            'target_jid': '120363410784518818@g.us'
        })
        self.assertEqual(res1_conn.status_code, 200)
        self.assertTrue(res1_conn.json()['is_leader'])

        # 5. Instance 2 heartbeats again - should now see status connected and can_send_now=True
        res2_chk = self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-2'
        })
        data2_chk = res2_chk.json()
        self.assertFalse(data2_chk['is_leader'])
        self.assertEqual(data2_chk['leader_state']['status'], 'connected')
        self.assertTrue(data2_chk['leader_state']['can_send_now'])
        self.assertIsNone(data2_chk['leader_state']['qr_data'])

    def test_failover_after_lease_expiry(self):
        # 1. Instance 1 becomes leader
        self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-dead',
            'status': 'connected'
        })

        # 2. Artificially expire the lease (> 15 seconds)
        db = SessionLocal()
        db.execute(text("UPDATE whatsapp_bot_lease SET heartbeat_at = NOW() - INTERVAL '20 seconds' WHERE id = 1"))
        db.commit()
        db.close()

        # 3. Instance 2 heartbeats - should detect expired lease and take over as leader!
        res_takeover = self.client.post('/api/v1/whatsapp/bot-cluster-heartbeat', json={
            'instance_id': 'test-node-alive',
            'instance_host': '172.31.0.99'
        })
        self.assertEqual(res_takeover.status_code, 200)
        data = res_takeover.json()
        self.assertTrue(data['is_leader'])
        self.assertEqual(data['leader_id'], 'test-node-alive')

    def test_outbound_queue_lifecycle(self):
        # 1. Follower enqueues message
        enq = self.client.post('/api/v1/whatsapp/bot-queue-enqueue', json={
            'target_type': 'direct',
            'target_jid': '919876543210@s.whatsapp.net',
            'message': 'Cluster Queue Test',
            'instance_id': 'test-node-follower'
        })
        self.assertEqual(enq.status_code, 200)
        qid = enq.json()['queue_id']

        # 2. Leader polls queue
        poll = self.client.get('/api/v1/whatsapp/bot-queue-poll?limit=5')
        self.assertEqual(poll.status_code, 200)
        items = poll.json()['items']
        matching = [it for it in items if it['id'] == qid]
        self.assertEqual(len(matching), 1)

        # 3. Leader reports completion
        comp = self.client.post('/api/v1/whatsapp/bot-queue-complete', json={
            'queue_id': qid,
            'status': 'sent',
            'result_payload': {'message_id': 'TEST-MSG-ID-999'}
        })
        self.assertEqual(comp.status_code, 200)
        self.assertTrue(comp.json()['success'])

        # 4. Follower verifies sent status
        chk = self.client.get(f'/api/v1/whatsapp/bot-queue-check?queue_id={qid}')
        self.assertEqual(chk.status_code, 200)
        self.assertEqual(chk.json()['status'], 'sent')
        self.assertEqual(chk.json()['result_payload']['message_id'], 'TEST-MSG-ID-999')


if __name__ == '__main__':
    unittest.main()
