let ratingChart = null;
let adrChart = null;
let comparisonPerformanceChart = null;
let comparisonCombatChart = null;

const $ = (id) => document.getElementById(id);

function number(value, digits = 2) {
    if (value === null || value === undefined || value === "") {
        return "--";
    }

    return Number(value).toFixed(digits);
}

function chartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: "index"
        },
        plugins: {
            legend: {
                labels: {
                    color: "#aab4c8",
                    usePointStyle: true
                }
            }
        },
        scales: {
            x: {
                ticks: { color: "#8792a8" },
                grid: { color: "#263044" }
            },
            y: {
                ticks: { color: "#8792a8" },
                grid: { color: "#263044" }
            }
        }
    };
}

function showError(element, message) {
    element.textContent = message;
}

async function loadPlayer(playerId) {
    if (!playerId) return;

    try {
        const response = await fetch(
            `/api/predictions/players/${playerId}/overview/`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Could not load player.");
        }

        const stats = data.statistics;

        $("avgRating").textContent = number(stats.avg_rating);
        $("avgAdr").textContent = number(stats.avg_adr);
        $("avgKast").textContent = number(stats.avg_kast) + "%";
        $("totalKills").textContent = Number(stats.total_kills || 0).toLocaleString();
        $("totalMaps").textContent = stats.total_maps ?? 0;
        $("avgImpact").textContent = number(stats.avg_impact);

        renderRatingChart(data.rating_trend);
        renderAdrChart(data.rating_trend);
        renderMapTable(data.map_performance);
        renderPlayerIntelligence(data.intelligence);

        $("comparePlayer1").value = playerId;

    } catch (error) {
        console.error(error);
        alert("Error loading player: " + error.message);
    }
}

function renderRatingChart(trend) {
    const labels = trend.map((item, index) => {
        return `${item.map} #${index + 1}`;
    });

    const values = trend.map(item => item.rating);

    if (ratingChart) ratingChart.destroy();

    ratingChart = new Chart($("ratingChart"), {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "Rating",
                data: values,
                borderColor: "#9875ff",
                backgroundColor: "rgba(152,117,255,0.13)",
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 4,
                pointBackgroundColor: "#b49aff"
            }]
        },
        options: chartOptions()
    });
}

function renderAdrChart(trend) {
    const labels = trend.map((item, index) => {
        return `${item.map} #${index + 1}`;
    });

    const values = trend.map(item => item.adr);

    if (adrChart) adrChart.destroy();

    adrChart = new Chart($("adrChart"), {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "ADR",
                data: values,
                backgroundColor: "rgba(76,157,255,0.75)",
                borderRadius: 5
            }]
        },
        options: chartOptions()
    });
}

function renderMapTable(maps) {
    const tbody = $("mapTable");
    tbody.innerHTML = "";

    if (!maps.length) {
        tbody.innerHTML = `
            <tr><td colspan="5" class="empty-cell">
                No map data available.
            </td></tr>`;
        return;
    }

    maps.forEach(map => {
        const row = document.createElement("tr");

        const values = [
            map.map__map_name,
            map.matches_count,
            number(map.avg_rating),
            number(map.avg_adr),
            number(map.avg_impact)
        ];

        values.forEach((value, index) => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "--";

            if (index === 0) cell.className = "map-name";
            if (index === 2) cell.className = "rating-cell";

            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });
}

async function comparePlayers() {
    const player1 = $("comparePlayer1").value;
    const player2 = $("comparePlayer2").value;

    if (!player1 || !player2) {
        alert("Please select both players.");
        return;
    }

    const button = $("compareButton");
    button.disabled = true;
    button.textContent = "Comparing...";

    try {
        const response = await fetch(
            `/api/predictions/compare/?player1_id=${player1}&player2_id=${player2}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Comparison failed.");
        }

        const first = data.comparison.player1;
        const second = data.comparison.player2;

        $("comparisonResult").textContent =
            `${first.username} vs ${second.username} · ` +
            `${first.statistics.total_maps} maps vs ` +
            `${second.statistics.total_maps} maps`;

        renderComparisonChart(first, second);

    } catch (error) {
        alert(error.message);
    } finally {
        button.disabled = false;
        button.textContent = "Compare Players";
    }
}


function renderComparisonChart(first, second) {
    const a = first.statistics;
    const b = second.statistics;

    const purple = "rgba(152,117,255,0.85)";
    const blue = "rgba(76,157,255,0.85)";

    // Performance: Rating and Impact
    if (comparisonPerformanceChart) {
        comparisonPerformanceChart.destroy();
    }

    comparisonPerformanceChart = new Chart(
        $("comparisonPerformanceChart"),
        {
            type: "bar",
            data: {
                labels: ["Rating", "Impact"],
                datasets: [
                    {
                        label: first.username,
                        data: [a.avg_rating, a.avg_impact],
                        backgroundColor: purple,
                        borderRadius: 6
                    },
                    {
                        label: second.username,
                        data: [b.avg_rating, b.avg_impact],
                        backgroundColor: blue,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                ...chartOptions(),
                scales: {
                    x: {
                        ticks: { color: "#aab4c8" },
                        grid: { color: "#263044" }
                    },
                    y: {
                        beginAtZero: true,
                        suggestedMax: 2,
                        ticks: { color: "#8792a8" },
                        grid: { color: "#263044" }
                    }
                }
            }
        }
    );

    // Combat: ADR and KAST
    if (comparisonCombatChart) {
        comparisonCombatChart.destroy();
    }

    comparisonCombatChart = new Chart(
        $("comparisonCombatChart"),
        {
            type: "bar",
            data: {
                labels: ["ADR", "KAST"],
                datasets: [
                    {
                        label: first.username,
                        data: [a.avg_adr, a.avg_kast],
                        backgroundColor: purple,
                        borderRadius: 6
                    },
                    {
                        label: second.username,
                        data: [b.avg_adr, b.avg_kast],
                        backgroundColor: blue,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                ...chartOptions(),
                scales: {
                    x: {
                        ticks: { color: "#aab4c8" },
                        grid: { color: "#263044" }
                    },
                    y: {
                        beginAtZero: true,
                        suggestedMax: 100,
                        ticks: { color: "#8792a8" },
                        grid: { color: "#263044" }
                    }
                }
            }
        }
    );

    renderComparisonInsights(first, second);
}

function renderComparisonInsights(first, second) {
    const a = first.statistics;
    const b = second.statistics;

    const kdA = a.total_deaths
        ? a.total_kills / a.total_deaths
        : 0;

    const kdB = b.total_deaths
        ? b.total_kills / b.total_deaths
        : 0;

    const hsA = a.total_kills
        ? (a.total_headshots / a.total_kills) * 100
        : 0;

    const hsB = b.total_kills
        ? (b.total_headshots / b.total_kills) * 100
        : 0;

    const metrics = [
        {
            name: "Average Rating",
            first: a.avg_rating,
            second: b.avg_rating
        },
        {
            name: "Average ADR",
            first: a.avg_adr,
            second: b.avg_adr
        },
        {
            name: "Average Impact",
            first: a.avg_impact,
            second: b.avg_impact
        },
        {
            name: "Average KAST",
            first: a.avg_kast,
            second: b.avg_kast
        },
        {
            name: "Kill / Death Ratio",
            first: kdA,
            second: kdB
        },
        {
            name: "Headshot Rate",
            first: hsA,
            second: hsB
        }
    ];

    const html = metrics.map(metric => {
        const firstValue = Number(metric.first || 0);
        const secondValue = Number(metric.second || 0);

        let winner = "Equal";
        let winnerValue = "Both players are equal";

        if (firstValue > secondValue) {
            winner = first.username;
            winnerValue = `${first.username} leads`;
        } else if (secondValue > firstValue) {
            winner = second.username;
            winnerValue = `${second.username} leads`;
        }

        const difference = Math.abs(firstValue - secondValue);

        return `
            <div class="insight-card">
                <span>${escapeHTML(metric.name)}</span>
                <strong>${escapeHTML(winner)}</strong>
                <small>
                    ${number(firstValue)} vs ${number(secondValue)}
                    · Difference: ${number(difference)}
                </small>
            </div>
        `;
    }).join("");

    $("comparisonInsights").innerHTML = html;

    $("comparisonResult").textContent =
        `${first.username} vs ${second.username} · ` +
        `${a.total_maps} maps vs ${b.total_maps} maps`;
}


async function predictRating() {
    const playerId = $("playerSelect").value;
    const mapName = $("predictionMap").value;

    if (!playerId) {
        alert("Please select a player first.");
        return;
    }

    const button = $("predictButton");
    const result = $("predictionResult");

    button.disabled = true;
    button.textContent = "Predicting...";

    try {
        const response = await fetch(
            `/api/predictions/predict/?player_id=${playerId}&map_name=${mapName}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            const error = Array.isArray(data.error)
                ? data.error.join(", ")
                : data.error;

            throw new Error(error || "Prediction failed.");
        }

        const prediction = data.prediction;

        result.innerHTML = `
            <div class="eyebrow">PREDICTED PLAYER RATING</div>
            <div class="prediction-value">
                ${number(prediction.predicted_rating, 4)}
            </div>
            <div class="prediction-meta">
                Player: ${escapeHTML(prediction.username)}<br>
                Map: ${escapeHTML(prediction.map_name)}<br>
                Historical maps: ${prediction.history_maps_count}<br>
                Model: ${escapeHTML(prediction.model_name)}<br>
                Features: ${prediction.feature_count}
            </div>
        `;

    } catch (error) {
        result.textContent = "Prediction error: " + error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Generate Prediction";
    }
}

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

document.addEventListener("DOMContentLoaded", () => {
    $("playerSelect").addEventListener("change", event => {
        loadPlayer(event.target.value);
    });

    $("compareButton").addEventListener("click", comparePlayers);
    $("predictButton").addEventListener("click", predictRating);

    const firstPlayer = $("playerSelect").value;

    if (firstPlayer) {
        loadPlayer(firstPlayer);
    }

    const navItems = document.querySelectorAll(".nav-item");

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");
        });
    });
});

function renderPlayerIntelligence(intelligence) {
    if (!intelligence) return;

    const trendElement = $("intelligenceTrend");
    const descriptionElement = $("intelligenceTrendDescription");

    const trendLabels = {
        improving: "Improving",
        declining: "Declining",
        stable: "Stable",
        insufficient_data: "Insufficient Data",
    };

    const trendDescriptions = {
        improving: "Your recent rating is higher than your previous performance.",
        declining: "Your recent rating is lower than your previous performance.",
        stable: "Your performance has remained relatively consistent.",
        insufficient_data: "More match data is needed to evaluate your performance trend.",
    };

    trendElement.textContent =
        trendLabels[intelligence.trend] || "Insufficient Data";

    descriptionElement.textContent =
        trendDescriptions[intelligence.trend] || trendDescriptions.insufficient_data;

    $("intelligenceRecentRating").textContent =
        intelligence.recent_avg_rating ?? "--";

    $("intelligencePreviousRating").textContent =
        intelligence.previous_avg_rating ?? "--";

    $("intelligenceStdDev").textContent =
        intelligence.rating_stddev !== null &&
        intelligence.rating_stddev !== undefined
            ? Number(intelligence.rating_stddev).toFixed(3)
            : "--";

    $("intelligenceSampleMessage").textContent =
        intelligence.sample_sufficient
            ? "Available match history is sufficient for basic analysis."
            : "At least 10 maps are recommended for more reliable analysis.";
}