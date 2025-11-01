const KPI = ({ label, value, trend }) => {
  return (
    <div className="kpi-card">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value ?? "—"}</span>
      {trend ? <span className="kpi-trend">{trend}</span> : null}
    </div>
  );
};

export default KPI;

