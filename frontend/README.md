# Trading App - Flutter Web Application

A modern Flutter web application for portfolio holdings visualization that connects to the FastAPI backend.

## Features

- **Portfolio Dashboard**: Overview with key metrics, sector allocation, and top holdings
- **Holdings Management**: Detailed holdings table with filtering and sorting
- **Interactive Charts**: Sector allocation pie charts and top holdings bar charts
- **Responsive Design**: Works on desktop, tablet, and mobile web browsers
- **Real-time Data**: Connects to FastAPI backend for live portfolio data
- **Material Design 3**: Modern UI with dark/light theme support

## Prerequisites

- [Flutter](https://flutter.dev/docs/get-started/install) (version 3.0 or higher)
- Web browser (Chrome, Firefox, Safari, or Edge)
- FastAPI backend running on `http://localhost:8000`

## Getting Started

### 1. Install Flutter

Follow the [Flutter installation guide](https://flutter.dev/docs/get-started/install) for your operating system.

### 2. Verify Installation

```bash
flutter doctor
```

Make sure web support is enabled:
```bash
flutter config --enable-web
```

### 3. Install Dependencies

```bash
cd frontend
flutter pub get
```

### 4. Start the Backend

Make sure the FastAPI backend is running:
```bash
cd ../backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Run the Web Application

```bash
cd frontend
flutter run -d chrome
```

Or run on a different browser:
```bash
flutter run -d web-server --web-port 8080
```

## Development

### Project Structure

```
frontend/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── models/                   # Data models
│   │   └── holdings.dart         # Holdings data structures
│   ├── providers/                # State management
│   │   └── holdings_provider.dart # API state providers
│   ├── screens/                  # Main app screens
│   │   ├── dashboard_screen.dart  # Portfolio overview
│   │   ├── holdings_screen.dart   # Holdings table
│   │   └── charts_screen.dart     # Analytics charts
│   ├── services/                 # API services
│   │   └── api_service.dart       # HTTP client
│   └── widgets/                  # Reusable components
│       ├── portfolio_summary_cards.dart
│       ├── sector_allocation_chart.dart
│       ├── top_holdings_chart.dart
│       ├── loading_widget.dart
│       └── error_widget.dart
├── web/
│   ├── index.html               # Web entry point
│   └── manifest.json            # PWA manifest
└── pubspec.yaml                 # Dependencies
```

### Key Dependencies

- **flutter_riverpod**: State management
- **http**: HTTP client for API calls
- **fl_chart**: Interactive charts
- **go_router**: Navigation
- **intl**: Internationalization and formatting

### API Configuration

The app connects to the FastAPI backend at `http://localhost:8000`. To change this:

1. Edit `lib/services/api_service.dart`
2. Update the `baseUrl` constant:
   ```dart
   static const String baseUrl = 'http://your-api-url:port';
   ```

## Building for Production

### Web Build

```bash
flutter build web
```

The built files will be in `build/web/` directory.

### Deployment

1. **Static Hosting** (Netlify, Vercel, GitHub Pages):
   ```bash
   flutter build web --base-href="/your-app-path/"
   ```

2. **Web Server** (nginx, Apache):
   ```bash
   flutter build web
   # Copy build/web/ contents to your web server
   ```

3. **Docker**:
   ```dockerfile
   FROM nginx:alpine
   COPY build/web /usr/share/nginx/html
   EXPOSE 80
   CMD ["nginx", "-g", "daemon off;"]
   ```

## Features Overview

### Dashboard
- Portfolio summary cards (total value, gain/loss, positions count)
- Sector allocation donut chart
- Top holdings bar chart
- Quick action buttons

### Holdings
- Searchable and filterable holdings table
- Sort by value, gain/loss, or ticker
- Filter by account or sector
- Responsive mobile/desktop layouts

### Charts
- Interactive sector allocation visualization
- Top holdings performance charts
- Portfolio performance summary
- Fullscreen chart viewing

## API Integration

The app consumes the following FastAPI endpoints:

- `GET /api/holdings/summary` - Portfolio overview
- `GET /api/holdings/positions` - Detailed positions
- `GET /api/instruments` - Instrument data
- `GET /api/health` - Health check

### Error Handling

- Network connectivity issues
- API timeout handling
- User-friendly error messages
- Retry mechanisms

## Responsive Design

The app adapts to different screen sizes:

- **Desktop (>1200px)**: Multi-column layouts, data tables
- **Tablet (800-1200px)**: Two-column grids, navigation rail
- **Mobile (<800px)**: Single column, bottom navigation

## Development Tips

### Hot Reload
```bash
flutter run -d chrome --hot
```

### Debugging
```bash
flutter run -d chrome --debug
```

### Testing
```bash
flutter test
```

### Code Generation (if using build_runner)
```bash
flutter packages pub run build_runner build
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Make sure FastAPI backend has CORS configured
2. **Network Issues**: Check backend URL in `api_service.dart`
3. **Build Errors**: Run `flutter clean && flutter pub get`
4. **Web Issues**: Ensure web support is enabled with `flutter config --enable-web`

### Browser Compatibility

- Chrome/Chromium: Full support
- Firefox: Full support
- Safari: Full support
- Edge: Full support

### Performance Tips

1. Use `flutter build web --release` for production
2. Enable caching for static assets
3. Optimize images and icons
4. Use lazy loading for large datasets

## Contributing

1. Follow Flutter/Dart style guidelines
2. Use meaningful commit messages
3. Test on multiple browsers
4. Update documentation for new features

## License

This project is part of the automated trading application suite.