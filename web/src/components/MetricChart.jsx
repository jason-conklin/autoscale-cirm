import "chartjs-adapter-date-fns";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
  TimeScale,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, TimeScale);

const colors = {
  cpu: {
    main: "rgba(37, 99, 235, 1)",
    fill: "rgba(37, 99, 235, 0.15)",
  },
  mem: {
    main: "rgba(99, 102, 241, 1)",
    fill: "rgba(99, 102, 241, 0.15)",
  },
  net: {
    main: "rgba(16, 185, 129, 1)",
    fill: "rgba(16, 185, 129, 0.15)",
  },
};

const MetricChart = ({ title, points = [], metricKey }) => {
  const color = colors[metricKey] || colors.cpu;
  const data = {
    labels: points.map((point) => point.timestamp),
    datasets: [
      {
        label: title,
        data: points.map((point) => point.value),
        borderColor: color.main,
        backgroundColor: color.fill,
        tension: 0.35,
        fill: true,
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      x: {
        type: "time",
        time: { tooltipFormat: "PPpp" },
        grid: { color: "rgba(226, 232, 240, 0.5)" },
      },
      y: {
        beginAtZero: true,
        grid: { color: "rgba(226, 232, 240, 0.5)" },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `${context.parsed.y?.toFixed(2)} ${metricKey === "net" ? "kbps" : "%"}`,
        },
      },
    },
  };

  return (
    <div className="panel" style={{ minHeight: "320px" }}>
      <div className="panel-header">
        <span className="panel-title">{title}</span>
      </div>
      <div style={{ height: 260 }}>
        <Line data={data} options={options} />
      </div>
    </div>
  );
};

export default MetricChart;

