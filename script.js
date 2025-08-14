// script.js

// Function to fetch signals from backend
async function fetchSignals() {
    try {
        const response = await fetch('/get_signals');
        const data = await response.json();

        const tableBody = document.querySelector("#signals-table tbody");
        tableBody.innerHTML = ""; // Clear existing rows

        data.forEach(signal => {
            const row = document.createElement("tr");

            // Symbol
            const symbolCell = document.createElement("td");
            symbolCell.textContent = signal.symbol;
            row.appendChild(symbolCell);

            // Timeframe
            const tfCell = document.createElement("td");
            tfCell.textContent = signal.timeframe;
            row.appendChild(tfCell);

            // Signal Type
            const signalCellType = document.createElement("td");
            signalCellType.textContent = signal.signal;
            signalCellType.classList.add(signal.signal.toLowerCase() === "buy" ? "buy" : "sell");
            row.appendChild(signalCellType);

            // Time
            const timeCell = document.createElement("td");
            timeCell.textContent = signal.time;
            row.appendChild(timeCell);

            tableBody.appendChild(row);
        });

    } catch (error) {
        console.error("Error fetching signals:", error);
    }
}

// Refresh signals every 5 seconds
setInterval(fetchSignals, 5000);

// Initial load
fetchSignals();
