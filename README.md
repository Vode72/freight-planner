# 🚛 Freight Planner

A full-stack Transport Management System (TMS) built as a portfolio project, demonstrating real-world logistics operations management.

## 🌐 Live Demo

> **Demo credentials:**
> - Username: `demo`
> - Password: `freight2024`

## 📸 Screenshots

![Trips List](screenshots/trips-list.png)
![Trip Detail](screenshots/trip-detail.png)
![Cost Calculator](screenshots/cost-calculator.png)

## ✨ Features

### Trip Management
- Create and manage transport trips (Trips) with full lifecycle tracking
- 5-stage status flow: Planned → Confirmed → In Progress → Delivered → Invoiced
- Visual status chain with forward/backward navigation
- Real-time capacity monitoring (weight, loading meters, volume)
- Ferry route selection with pricing (4 routes: Finland → Germany/Belgium)

### Order Management
- Create transport orders (Orders) independently
- Assign orders to trips with automatic capacity validation
- Prevents over-capacity loading with warnings
- Auto-generated order references (HEL-2026-001 format)

### Cost Management
- 18 cost codes organized in logical groups (100-820)
- Revenue vs. cost tracking per trip
- Automatic margin calculation
- Invoice confirmation with lock mechanism

### Cost Calculator
- Standalone quotation and margin calculator
- Domestic and continental km-based pricing
- Fuel surcharge calculation
- Toll options: Germany / Germany + Netherlands
- Ferry route pricing with 4 predefined routes
- Real-time margin % → selling price calculation

### Equipment Pools
- **Trailer pool:** 12 trailers (TIP Trailer Services leasing)
  - Box trailers (URV), Side-opening (SRV), Dual-temp (TRV)
  - Curtain trailers (CRT), Mega trailers (HRV)
- **Carrier pool:** 6 fictional carriers (3 Finnish, 3 European)

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, JavaScript |
| Backend | Python 3, Flask, Flask-CORS |
| Database | SQLite |
| API | REST |
| Styling | Inline CSS (dark theme) |

## 🚀 Getting Started

### Prerequisites
- Node.js (v16+)
- Python 3.8+
- npm

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/Vode72/freight-planner.git
cd freight-planner
```

**2. Set up backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
python init_db.py
python app.py
```
Backend runs at `http://127.0.0.1:5000`

**3. Set up frontend**
```bash
cd ../frontend
npm install
npm start
```
Frontend runs at `http://localhost:3000`

**4. Login**
- Username: `demo`
- Password: `freight2024`

## 📁 Project Structure

freight-planner/
├── backend/
│   ├── app.py          # Flask REST API (~700 lines)
│   ├── init_db.py      # Database setup + seed data
│   └── requirements.txt
└── frontend/
└── src/
└── components/
├── Login.js
├── TripList.js
├── TripDetail.js
├── TripForm.js
├── OrderList.js
├── OrderForm.js
└── CostCalculator.js

## 🗄️ Database Schema

| Table | Description |
|---|---|
| `trips` | Transport trips with route, equipment, schedule |
| `orders` | Individual shipments with cargo details |
| `costs` | Cost lines per trip (revenues + costs) |
| `trailers` | Trailer pool (TIP Trailer Services) |
| `carriers` | Carrier pool (fictional companies) |

## 💡 Business Logic

- **Capacity validation:** Adding an order to a trip checks weight, loading meters and volume against trailer specs
- **Status locking:** Invoiced trips are fully locked — no edits possible
- **Cost codes:** Organized in 100-series groups (100=revenue, 200=fuel, 300=tolls, 400=trailer, 500=ferry, 600=surcharges, 700=handling, 800=post-delivery)
- **Auto-references:** Order references generated automatically (HEL-YYYY-NNN)

## 🔮 Planned Enhancements

- [ ] Stepped TripForm (Orders → Equipment → Route → Summary)
- [ ] Order-to-Trip flow (assign order directly from order list)
- [ ] CMR freight document PDF generation
- [ ] Document storage per Trip/Order (ADR, Invoice)
- [ ] Route optimization and loading order suggestions
- [ ] EU 561/2006 driver rest time simulation
- [ ] Unloading time estimates per stop
- [ ] Map-based trailer tracking

## 👨‍💻 Author

Built by Toni Voutilainen — combining 12+ years of logistics industry experience with full-stack development skills.

> *"This project was built to demonstrate how domain expertise and technical skills combine — not just to learn to code, but to build tools that solve real logistics problems."*

---

*Built with React + Flask + SQLite · Dark TMS theme · Demo credentials: demo / freight2024*