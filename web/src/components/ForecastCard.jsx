import { format, formatDistanceToNow } from "date-fns";

const ForecastCard = ({ forecasts = [] }) => {
  const upcoming = forecasts
    .filter((item) => item.predicted_breach_time)
    .sort((a, b) => new Date(a.predicted_breach_time) - new Date(b.predicted_breach_time));

  if (upcoming.length === 0) {
    return (
      <div className="panel forecast-card">
        <div className="forecast-item clear">
          <div className="forecast-title">All clear</div>
          <div className="forecast-meta">No threshold breaches predicted within the lookahead window.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel forecast-card">
      {upcoming.slice(0, 3).map((item) => {
        const eta = new Date(item.predicted_breach_time);
        const confidenceValue =
          item.confidence !== null && item.confidence !== undefined
            ? Math.min(1, Math.max(0, item.confidence))
            : null;
        return (
          <div key={`${item.resource_id}-${item.metric}`} className="forecast-item">
            <div className="forecast-title">
              {item.resource_id} · {item.metric.toUpperCase()}
            </div>
            <div className="forecast-meta">
              <span>{format(eta, "PPpp")}</span>
              <span className="badge">ETA {formatDistanceToNow(eta, { addSuffix: true })}</span>
            </div>
            <div className="forecast-meta">
              <span className="badge">
                Confidence: {confidenceValue !== null ? `${(confidenceValue * 100).toFixed(0)}%` : "n/a"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ForecastCard;
