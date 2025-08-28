// static/dashboard.js

document.addEventListener("DOMContentLoaded", () => {
    const signalTableBody = document.querySelector("#signals-table tbody");
    const lastUpdated = document.getElementById("last-update");
    const toggle = document.getElementById("mode-toggle");
    const label = document.getElementById("mode-label");

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
                directionCell.textContent = signal.direction || signal.signal;
                directionCell.classList.add((signal.direction || signal.signal).toLowerCase());
                row.appendChild(directionCell);

                const timeframeCell = document.createElement("td");
                timeframeCell.textContent = signal.timeframe;
                row.appendChild(timeframeCell);

                const timeCell = document.createElement("td");
                timeCell.textContent = signal.time;
                row.appendChild(timeCell);

                const receivedCell = document.createElement("td");
                receivedCell.textContent = new Date().toISOString().slice(0,19).replace("T"," ");
                row.appendChild(receivedCell);

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

    // Initialize dashboard state from backend
    fetch("/signals_data")
        .then(res => res.json())
        .then(data => {
            toggle.checked = (data.mode === "LIVE");
            label.innerText = data.mode === "LIVE" ? "Live Mode" : "Test Mode";
            lastUpdated.textContent = data.last_update;
        });

    // Handle toggle click
    toggle.addEventListener("change", function() {
        fetch("/toggle_mode", {method: "POST"})
            .then(res => res.json())
            .then(data => {
                label.innerText = data.mode === "LIVE" ? "Live Mode" : "Test Mode";
            });
    });

    // Socket.IO listener for new signals
    const socket = io();
    socket.on('new_signal', function(data) {
        const row = signalTableBody.insertRow();
        row.insertCell(0).innerText = data.symbol;
        row.insertCell(1).innerText = data.signal;
        row.insertCell(2).innerText = data.time;
        row.insertCell(3).innerText = data.timeframe;
        row.insertCell(4).innerText = new Date().toISOString().slice(0,19).replace("T"," ");

        lastUpdated.textContent = data.time;

        while(signalTableBody.rows.length > 50){
            signalTableBody.deleteRow(0);
        }
    });
});
