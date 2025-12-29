# MCP Platform Frontend

Modern web application for the MCP Platform, built with React 18, TypeScript, and Vite.

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5
- **Routing**: React Router v6
- **State Management**: 
  - Zustand (UI state and global state)
  - TanStack Query v5 (server state and data fetching)
- **UI Components**: shadcn/ui (based on Radix UI)
- **Styling**: Tailwind CSS 3
- **Form Handling**: React Hook Form + Zod
- **HTTP Client**: Axios
- **Testing**: Vitest + React Testing Library + fast-check

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

### Building

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Testing

```bash
# Run tests once
npm run test

# Run tests in watch mode
npm run test:watch
```

### Code Quality

```bash
# Run ESLint
npm run lint

# Format code with Prettier
npm run format

# Type check
npm run type-check
```

## Environment Variables

Copy `.env.example` to `.env.development` and configure:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENABLE_ANALYTICS=false
VITE_ENV=development
```

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── assets/         # Images, fonts, etc.
│   ├── components/     # Reusable components
│   │   ├── ui/        # shadcn/ui base components
│   │   ├── layout/    # Layout components
│   │   ├── forms/     # Form components
│   │   └── common/    # Common components
│   ├── features/      # Feature modules
│   │   ├── auth/     # Authentication
│   │   ├── tools/    # MCP tool management
│   │   ├── knowledge/# Knowledge base
│   │   ├── analysis/ # AI analysis
│   │   ├── github/   # GitHub integration
│   │   ├── deployments/ # Deployment management
│   │   └── dashboard/   # Dashboard
│   ├── hooks/        # Custom hooks
│   ├── lib/          # Utility functions and config
│   ├── services/     # API services
│   ├── stores/       # Zustand stores
│   ├── types/        # TypeScript type definitions
│   ├── test/         # Test utilities
│   ├── App.tsx       # Root component
│   ├── main.tsx      # Entry point
│   └── router.tsx    # Route configuration
├── .env.example      # Environment variables template
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier
- `npm run type-check` - Run TypeScript type checking
- `npm run test` - Run tests once
- `npm run test:watch` - Run tests in watch mode

## License

See the LICENSE file in the root directory.
