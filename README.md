# Automated Trading Application - Phase 1

A modern web application for portfolio visualization and holdings management, built with FastAPI (Python) backend and Flutter web frontend.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ with pip
- Flutter SDK 3.x
- Modern web browser (Chrome/Edge recommended)

### 1. Start Backend API (Terminal 1)
```bash
cd backend
pip install -r requirements.txt
python -c "import uvicorn; uvicorn.run('main:app', host='127.0.0.1', port=8001, log_level='error')"
```

### 2. Start Frontend Web App (Terminal 2)
```bash
cd frontend
flutter pub get
flutter run -d web-server --web-port 3000
```

### 3. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## 📊 Features

### Portfolio Dashboard
- **$13.4M Portfolio** with real-time market data
- **45 Holdings** across 10 trading accounts
- **Interactive Charts** for sector allocation and top holdings
- **Auto-refresh** every 30 seconds
- **Responsive Design** for all screen sizes

### Holdings Management
- **Detailed Position Table** with sorting and filtering
- **Search by Ticker/Company** with real-time results
- **Account & Sector Filtering** for focused analysis
- **Mobile-optimized Cards** for smaller screens
- **Real-time Gain/Loss** calculations with color coding

### Technical Features
- **RESTful API** with FastAPI and automatic OpenAPI docs
- **SQLite Database** with 217 instruments and real portfolio data
- **Yahoo Finance Integration** for live market pricing
- **Material Design 3** UI with smooth animations
- **Error Handling** with user-friendly messages

## 🛠 Architecture

```
Frontend (Flutter Web)  ←→  Backend (FastAPI)  ←→  SQLite DB
     Port 3000               Port 8001              portfolio.db
                                 ↓
                         Yahoo Finance API
```

## 📁 Project Structure

```
automated-trader/
├── backend/                 # FastAPI backend
│   ├── api/                # REST API endpoints
│   ├── services/           # Business logic
│   ├── models/             # Data models
│   ├── database/           # Database layer
│   └── portfolio.db        # SQLite database (303KB)
├── frontend/               # Flutter web frontend
│   ├── lib/
│   │   ├── screens/        # UI screens
│   │   ├── widgets/        # Reusable components
│   │   ├── providers/      # State management
│   │   ├── models/         # Data models
│   │   └── services/       # API services
│   └── web/                # Web build output
└── PHASE_1_COMPLETION_REPORT.md  # Detailed documentation
```

## 🔧 Development

### Backend Development
```bash
cd backend
python main.py              # Development server
python -m pytest           # Run tests
```

### Frontend Development
```bash
cd frontend
flutter analyze            # Static analysis
flutter test               # Run tests
flutter build web          # Production build
```

### API Testing
```bash
# Test portfolio summary
curl "http://localhost:8001/api/holdings/summary"

# Test positions with filtering
curl "http://localhost:8001/api/holdings/positions?limit=10"

# View API documentation
open http://localhost:8001/docs
```

## 📈 Portfolio Data

- **Total Value**: $13,476,779.41
- **Top Holdings**: MSFT ($4.5M), NVDA ($1.9M), GOOGL ($680K)
- **Sectors**: Technology (27%), Communication (6%), Consumer (1%)
- **Accounts**: 10 trading accounts with individual tracking
- **Update Frequency**: Real-time via Yahoo Finance API

## 🔍 API Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /api/holdings/summary` | Portfolio overview | Total value, accounts, sectors |
| `GET /api/holdings/positions` | Position details | Holdings with filtering |
| `GET /api/holdings/accounts` | Account information | Account balances |
| `GET /api/instruments/` | Instrument search | Security lookup |
| `GET /health` | Health check | API status |

## 🚀 Phase 2 Roadmap

- **Mobile Apps**: Native iOS/Android with Flutter
- **Real-time Streaming**: WebSocket data feeds
- **Trade Execution**: Brokerage API integration
- **Advanced Analytics**: Technical indicators, risk metrics
- **Cloud Deployment**: AWS/Azure production deployment

## 📝 Documentation

For comprehensive documentation, see [PHASE_1_COMPLETION_REPORT.md](./PHASE_1_COMPLETION_REPORT.md)

## 🐛 Issues & Support

Current limitations:
- Single-user system (no authentication)
- Read-only portfolio data
- Yahoo Finance rate limits may affect data updates
- Some package dependencies have newer versions available

## 📄 License

This project is part of a multi-phase automated trading application development.

---

**Status**: Phase 1 Complete ✅  
**Last Updated**: September 14, 2025  
**Next Phase**: Mobile Application Development
