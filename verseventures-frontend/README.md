# VerseVentures Frontend

A modern React application for the VerseVentures platform, providing a comprehensive customer-facing website for managing subscriptions, API access, and biblical semantic search services.

## Features

### 🏠 **Homepage**

- Modern hero section with call-to-action
- Feature highlights and statistics
- Responsive design for all devices

### 🔐 **Authentication**

- User registration with email verification
- Login/logout functionality
- Google OAuth integration
- Protected routes for authenticated users

### 💳 **Subscription Management**

- View current subscription status
- Upgrade/downgrade plans
- Billing history and management
- Stripe integration for payments

### 🔑 **API Key Management**

- Create and manage API keys
- View usage statistics
- Secure key storage and display
- Copy-to-clipboard functionality

### 📊 **Dashboard**

- Usage statistics and analytics
- Quick access to key features
- Subscription status overview
- API key management interface

### 💰 **Pricing Page**

- Transparent pricing plans
- Feature comparison
- Monthly/annual billing options
- FAQ section

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS framework
- **Headless UI** - Accessible UI components
- **Heroicons** - Beautiful SVG icons
- **Axios** - HTTP client for API calls

## Getting Started

### Prerequisites

- Node.js 16+
- npm or yarn
- Backend API server running (see main README)

### Installation

1. **Clone the repository**

   ```bash
   cd verseventures-frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Environment Configuration**
   Create a `.env` file in the root directory:

   ```env
   REACT_APP_API_URL=http://localhost:8000
   ```

4. **Start the development server**

   ```bash
   npm start
   ```

   The application will be available at `http://localhost:3000`

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## Project Structure

```
src/
├── components/
│   ├── layout/          # Layout components (Header, Footer)
│   ├── pages/           # Page components
│   └── ui/              # Reusable UI components
├── contexts/            # React contexts (Auth)
├── services/            # API services
├── types/               # TypeScript interfaces
├── App.tsx              # Main app component
└── index.tsx            # App entry point
```

## Key Components

### Authentication Flow

- **AuthContext**: Manages user authentication state
- **ProtectedRoute**: Guards routes requiring authentication
- **PublicRoute**: Redirects authenticated users away from auth pages

### API Integration

- **api.ts**: Centralized API service with interceptors
- **Error handling**: Automatic token refresh and error handling
- **Type safety**: Full TypeScript integration

### Responsive Design

- Mobile-first approach with Tailwind CSS
- Responsive navigation with mobile menu
- Optimized for all screen sizes

## Environment Variables

| Variable            | Description     | Default                 |
| ------------------- | --------------- | ----------------------- |
| `REACT_APP_API_URL` | Backend API URL | `http://localhost:8000` |

## API Endpoints

The frontend integrates with the following backend endpoints:

### Authentication

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/verify-email` - Email verification
- `GET /auth/profile` - Get user profile

### Subscriptions

- `GET /subscriptions/current` - Get current subscription
- `POST /subscriptions/create-checkout-session` - Create Stripe checkout
- `POST /subscriptions/create-portal-session` - Access Stripe portal

### API Keys

- `GET /api-keys` - List API keys
- `POST /api-keys` - Create new API key
- `DELETE /api-keys/{id}` - Delete API key

### Usage Statistics

- `GET /aws/usage` - Get usage statistics
- `POST /aws/credentials` - Get temporary AWS credentials

## Styling

The application uses Tailwind CSS with custom components:

### Custom Classes

- `.btn-primary` - Primary button styling
- `.btn-secondary` - Secondary button styling
- `.input-field` - Form input styling

### Color Scheme

- Primary: Blue (`primary-600`)
- Success: Green
- Warning: Yellow
- Error: Red
- Neutral: Gray scale

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development

### Code Style

- TypeScript strict mode enabled
- ESLint configuration included
- Prettier formatting
- Component-based architecture

### State Management

- React Context for global state
- Local state with useState/useReducer
- No external state management libraries

### Performance

- Code splitting with React.lazy
- Optimized bundle size
- Lazy loading of components
- Efficient re-renders

## Deployment

### Build for Production

```bash
npm run build
```

### Environment Setup

Ensure all environment variables are set for production:

- `REACT_APP_API_URL` - Production API URL

### Static Hosting

The build output can be deployed to any static hosting service:

- Netlify
- Vercel
- AWS S3
- GitHub Pages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the VerseVentures platform. See the main repository for license information.

## Support

For support and questions:

- Check the documentation
- Open an issue on GitHub
- Contact the development team
