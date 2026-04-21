let dominanceChart;
let trendChart;
let trendData = [];

async function load() {

    const res = await fetch("/metrics");
    const data = await res.json();

    const o = data.orchestrator || {};

    // -------------------------
    // SYSTEM
    // -------------------------
    document.getElementById("system").innerHTML = `
        cycles: ${o.cycle_count || 0}<br>
        signals: ${o.last_signal_count || 0}<br>
        events: ${o.last_event_count || 0}
    `;

    // -------------------------
    // DOMINANCE
    // -------------------------
    const labels = (o.dominance || []).map(d => d.topic);
    const values = (o.dominance || []).map(d => d.score);

    if (!dominanceChart) {
        dominanceChart = new Chart(
            document.getElementById("dominanceChart"),
            {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [{ data: values }]
                }
            }
        );
    } else {
        dominanceChart.data.labels = labels;
        dominanceChart.data.datasets[0].data = values;
        dominanceChart.update();
    }

    // -------------------------
    // TREND
    // -------------------------
    trendData.push(o.last_signal_count || 0);
    if (trendData.length > 20) trendData.shift();

    if (!trendChart) {
        trendChart = new Chart(
            document.getElementById("trendChart"),
            {
                type: "line",
                data: {
                    labels: trendData.map((_, i) => i),
                    datasets: [{ data: trendData }]
                }
            }
        );
    } else {
        trendChart.data.labels = trendData.map((_, i) => i);
        trendChart.data.datasets[0].data = trendData;
        trendChart.update();
    }

    // -------------------------
    // ANOMALIES
    // -------------------------
    document.getElementById("anomalies").innerHTML =
        (o.anomalies || [])
        .map(a => `⚠ ${a.title || a.type || "anomaly"} → ${a.topic || ""}`)
        .join("<br>") || "none";

    // -------------------------
    // TOP SIGNAL
    // -------------------------
    if (o.dominance && o.dominance.length > 0) {
        const top = o.dominance[0];
        document.getElementById("top").innerHTML =
            `${top.topic} (${top.score})`;
    }

    // -------------------------
    // FLOW
    // -------------------------
    document.getElementById("flow").innerHTML =
        (o.dominance || [])
        .slice(0, 10)
        .map(d => `→ ${d.topic}`)
        .join("<br>");
}

async function sendEvent() {

    const topic = document.getElementById("topic").value;
    const type = document.getElementById("type").value;

    await fetch(`/event?user_id=admin&type=${type}&topic=${topic}`);
}

load();
setInterval(load, 3000);
