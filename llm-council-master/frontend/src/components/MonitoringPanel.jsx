import './MonitoringPanel.css';

const statusLabels = {
  healthy: 'Healthy',
  idle: 'Idle',
  running: 'In progress',
  error: 'Error',
  degraded: 'Degraded',
  unhealthy: 'Unavailable',
  not_configured: 'Not configured',
  unknown: 'Unknown',
  unavailable: 'Unavailable',
};

function StatusRow({ label, check }) {
  const status = check?.status || 'unknown';
  return (
    <div className="monitoring-row">
      <span>{label}</span>
      <span className={`monitoring-status monitoring-status-${status}`}>
        <span className="monitoring-status-dot" aria-hidden="true" />
        {statusLabels[status] || status}
      </span>
      {check?.latency_ms != null && (
        <span className="monitoring-latency">{check.latency_ms} ms</span>
      )}
      {check?.message && (
        <span className="monitoring-detail">{check.message}</span>
      )}
    </div>
  );
}

export default function MonitoringPanel({ health, councilActivity }) {
  const checkedAt = health?.checked_at
    ? new Date(health.checked_at).toLocaleTimeString()
    : null;

  return (
    <section className="monitoring-panel" aria-label="Service monitoring" aria-live="polite">
      <h2>System status</h2>
      <StatusRow
        label="Backend API"
        check={health?.checks?.api || {
          status: 'unknown',
          message: 'Waiting for first health check',
        }}
      />
      <StatusRow
        label="OpenRouter"
        check={health?.checks?.openrouter || {
          status: 'unknown',
          message: 'Waiting for first health check',
        }}
      />
      <StatusRow
        label="Council"
        check={{
          status: councilActivity?.status || 'idle',
          message: councilActivity?.message || 'Council is idle',
        }}
      />
      <div className="monitoring-updated">
        {checkedAt ? `Checked ${checkedAt}` : 'Checking services...'}
      </div>
    </section>
  );
}
