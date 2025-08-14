# Binary Options Trading Bot Web App

## 📌 Overview
This project is a **Flask-based web application** that connects to the **Twelve Data API** for real-time market data and applies a **custom binary options strategy** using:
- **Alligator Indicator**
- **EMA-150**
- **Stochastic Oscillator**
- **Price Action & Historical Pattern Analysis**

The app allows you to:
- View real-time signals for **1m, 2m, 3m, and 5m** timeframes.
- Display all qualifying signals in a clear dashboard table.
- Automatically refresh market data every 5 minutes.
- Fully responsive design with HTML/CSS/JavaScript.

---

## ⚡ Features
- Live scanning of **60 most popular currency pairs**.
- Real-time dashboard for multiple timeframes.
- No authentication or login required.
- Lightweight in-memory caching for reduced API calls.
- Mobile-friendly and optimized for fast loading.

---

## 🛠 Technology Stack
- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS, JavaScript
- **API:** [Twelve Data API](https://twelvedata.com/)
- **Hosting:** Render / Railway

---

## 🔑 Environment Variables
Store your credentials securely in a `.env` file:

```env
TWELVE_DATA_API_KEY=your_api_key_here
