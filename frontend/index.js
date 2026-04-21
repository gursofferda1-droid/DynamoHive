async function load() {

    const res = await fetch("/metrics");
    const data = await res.json();

    const o = data.orchestrator || {};

    document.getElementById("system").innerHTML = `
        cycles: ${o.cycle_count || 0}<br>
        signals: ${o.last_signal_count || 0}<br>
        events: ${o.last_event_count || 0}
    `;

    const labels = (o.dominance || []).map(d => d.topic);
    const values = (o.dominance || []).map(d => d.score);

    if (dominanceChart) {
        dominanceChart.data.labels = labels;
        dominanceChart.data.datasets[0].data = values;
        dominanceChart.update();
    }

    document.getElementById("anomalies").innerHTML =
        (o.anomalies || [])
        .map(a => `⚠ ${a.title || a.type || "anomaly"} → ${a.topic || ""}`)
        .join("<br>") || "none";
}

setInterval(load, 3000);
load();
