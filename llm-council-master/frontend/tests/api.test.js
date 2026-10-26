import assert from 'node:assert/strict';
import test from 'node:test';
import { api } from '../src/api.js';

test('health client reports endpoint latency', async (t) => {
  const payload = {
    status: 'healthy',
    checked_at: '2026-01-01T00:00:00+00:00',
    checks: {
      api: { status: 'healthy', message: 'API is responding' },
      openrouter: { status: 'healthy' },
    },
  };
  t.mock.method(globalThis, 'fetch', async (url) => {
    assert.equal(url, 'http://localhost:8001/api/health');
    return { ok: true, json: async () => structuredClone(payload) };
  });

  const health = await api.getHealth();

  assert.equal(health.status, 'healthy');
  assert.equal(health.checks.api.status, 'healthy');
  assert.equal(typeof health.checks.api.latency_ms, 'number');
  assert.ok(health.checks.api.latency_ms >= 0);
});

test('health client surfaces HTTP failures', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => ({
    ok: false,
    status: 503,
  }));

  await assert.rejects(api.getHealth(), /Health check failed with status 503/);
});

test('stream parser handles partial chunks and multiple events', async (t) => {
  const chunks = [
    'data: {"type":"stage1_',
    'start"}\r\n\r\ndata: {"type":"stage1_complete","data":[1]}\n\n',
  ];
  t.mock.method(globalThis, 'fetch', async () => ({
    ok: true,
    body: new ReadableStream({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(new TextEncoder().encode(chunk));
        }
        controller.close();
      },
    }),
  }));
  const events = [];

  await api.sendMessageStream('conversation-id', 'question', (type, event) => {
    events.push([type, event]);
  });

  assert.deepEqual(events, [
    ['stage1_start', { type: 'stage1_start' }],
    ['stage1_complete', { type: 'stage1_complete', data: [1] }],
  ]);
});
