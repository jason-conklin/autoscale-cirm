import { format } from "date-fns";

const AlertList = ({ alerts = [] }) => {
  if (!alerts.length) {
    return (
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Alert History</span>
        </div>
        <div className="empty-state">No alerts recorded yet.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Alert History</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Resource</th>
              <th>Metric</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <tr key={alert.id}>
                <td>{format(new Date(alert.created_at), "PPpp")}</td>
                <td>{alert.resource_id}</td>
                <td>{alert.metric.toUpperCase()}</td>
                <td>{alert.channel}</td>
                <td>
                  <span className={`status-pill ${alert.status}`}>
                    <span>●</span>
                    {alert.status}
                  </span>
                </td>
                <td>{alert.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AlertList;

