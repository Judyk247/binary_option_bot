// static/dashboard.js

document.addEventListener("DOMContentLoaded", () => {
    const signalTableBody = document.querySelector("#signalTable tbody");
    const lastUpdated = document.getElementById("lastUpdated");

    // Function to fetch signals from backend
    async function fetchSignals() {
        try {
            const response = await fetch("/get_signals");
            const data = await response.json();

            // Clear old rows
            signalTableBody.innerHTML = "";

            // Populate table with signals
            data.signals.forEach(signal => {
                const row = document.createElement("tr");

                const symbolCell = document.createElement("td");
                symbolCell.textContent = signal.symbol;
                row.appendChild(symbolCell);

                const directionCell = document.createElement("td");
                directionCell.textContent = signal.direction;
                directionCell.classList.add(signal.direction.toLowerCase()); // color coding
                row.appendChild(directionCell);

                const timeframeCell = document.createElement("td");
                timeframeCell.textContent = signal.timeframe;
                row.appendChild(timeframeCell);

                const timeCell = document.createElement("td");
                timeCell.textContent = signal.time;
                row.appendChild(timeCell);

                signalTableBody.appendChild(row);
            });

            // Update last refresh timestamp
            const now = new Date();
            lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        } catch (error) {
            console.error("Error fetching signals:", error);
        }
    }

    // Initial fetch
    fetchSignals();

    // Auto-refresh every 60 seconds
    setInterval(fetchSignals, 60000);
});
