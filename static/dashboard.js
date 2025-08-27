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

<script>
        const socket = io();

        // Initialize dashboard state from backend
        fetch("/signals_data")
            .then(res => res.json())
            .then(data => {
                const toggle = document.getElementById("mode-toggle");
                const label = document.getElementById("mode-label");

                toggle.checked = (data.mode === "LIVE");
                label.innerText = data.mode === "LIVE" ? "Live Mode" : "Test Mode";

                document.getElementById("last-update").innerText = data.last_update;

                const table = document.getElementById('signals-table').getElementsByTagName('tbody')[0];
                table.innerHTML = "";
                data.signals.forEach(sig => {
                    const row = table.insertRow();
                    row.insertCell(0).innerText = sig.symbol;
                    row.insertCell(1).innerText = sig.signal;
                    row.insertCell(2).innerText = sig.time;
                    row.insertCell(3).innerText = sig.timeframe;
                    row.insertCell(4).innerText = new Date().toISOString().slice(0,19).replace("T"," ");
                });
            });

        // Handle toggle click
        document.getElementById("mode-toggle").addEventListener("change", function() {
            fetch("/toggle_mode", {method: "POST"})
                .then(res => res.json())
                .then(data => {
                    document.getElementById("mode-label").innerText = 
                        data.mode === "LIVE" ? "Live Mode" : "Test Mode";
                });
        });

        // Listen for new signals
        socket.on('new_signal', function(data) {
            const table = document.getElementById('signals-table').getElementsByTagName('tbody')[0];

            const row = table.insertRow();
            row.insertCell(0).innerText = data.symbol;
            row.insertCell(1).innerText = data.signal;
            row.insertCell(2).innerText = data.time;
            row.insertCell(3).innerText = data.timeframe;
            row.insertCell(4).innerText = new Date().toISOString().slice(0,19).replace("T"," ");

            document.getElementById('last-update').innerText = data.time;

            while(table.rows.length > 50){
                table.deleteRow(0);
            }
        });
