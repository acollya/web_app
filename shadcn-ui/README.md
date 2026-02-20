# Acollya PWA - Mental Health Application

A comprehensive Progressive Web Application for mental health support, featuring mood tracking, journaling, AI chat, self-care programs, and therapy appointment booking.

## 🚀 Features

### Core Features
- **Mood Check-ins** - Daily emotional tracking with intensity ratings
- **Journal** - Private journaling with AI-generated reflections
- **AI Chat** - Conversational support and guidance
- **Self-Care Programs** - Structured mental health programs with chapters
- **Therapy Appointments** - Book and manage sessions with licensed therapists
- **Analytics** - Visualize your mental health journey over time

### Premium Features
- Unlimited chat messages
- Access to all self-care programs
- Priority therapist booking
- Advanced analytics
- Ad-free experience

## 🛠️ Technology Stack

### Frontend
- **React 19** with TypeScript
- **Vite** for blazing-fast builds
- **Tailwind CSS** + **Shadcn/ui** for beautiful UI
- **React Router** for navigation
- **React Query** for server state management

### Backend & Services
- **Supabase** - Database, Authentication, Edge Functions
- **Stripe** - Payment processing and subscriptions
- **Firebase Analytics** - User behavior tracking

## 📦 Installation

### Prerequisites
- Node.js 18 or higher
- pnpm (recommended) or npm

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd shadcn-ui
```

2. **Install dependencies**
```bash
pnpm install
```

3. **Set up environment variables**
```bash
cp .env.example .env.local
```

4. **Run in demo mode (no backend required)**
```bash
pnpm run dev
```

The app will run at `http://localhost:5173` in demo mode using localStorage.

## 🔧 Configuration

### Demo Mode (Default)

The app runs in demo mode by default, which:
- Uses localStorage for data persistence
- Provides mock authentication
- Simulates all backend operations
- Perfect for development and testing

No configuration needed! Just run `pnpm run dev`.

### Production Mode

To enable full backend integration:

1. **Set up Supabase** (see [SETUP_GUIDE.md](./SETUP_GUIDE.md))
   - Create a Supabase project
   - Run the database schema
   - Deploy Edge Functions
   - Get your API keys

2. **Set up Stripe** (see [SETUP_GUIDE.md](./SETUP_GUIDE.md))
   - Create products and prices
   - Configure webhooks
   - Get your API keys

3. **Set up Firebase** (see [SETUP_GUIDE.md](./SETUP_GUIDE.md))
   - Create a Firebase project
   - Enable Analytics
   - Get your configuration

4. **Update .env.local**
```env
# Supabase
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Stripe
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key

# Firebase
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_FIREBASE_MEASUREMENT_ID=G-your_measurement_id

# Mode
VITE_APP_MODE=production
```

5. **Run the app**
```bash
pnpm run dev
```

## 📚 Documentation

- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** - Complete setup instructions for all services
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Technical architecture and data flow
- **[INTEGRATION_PLAN.md](./INTEGRATION_PLAN.md)** - Integration roadmap and checklist

## 🗂️ Project Structure

```
shadcn-ui/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ui/             # Shadcn/ui components
│   │   ├── Layout.tsx      # App layout wrapper
│   │   ├── PageHeader.tsx  # Page header component
│   │   └── ...
│   ├── contexts/           # React contexts
│   │   └── AuthContext.tsx # Authentication context
│   ├── hooks/              # Custom React hooks
│   │   └── useAuth.ts      # Auth hook
│   ├── lib/                # Library configurations
│   │   ├── supabase.ts     # Supabase client
│   │   ├── stripe.ts       # Stripe client
│   │   ├── firebase.ts     # Firebase Analytics
│   │   └── utils.ts        # Utility functions
│   ├── pages/              # Application pages
│   │   ├── Home.tsx        # Home page
│   │   ├── MoodCheckin.tsx # Mood tracking
│   │   ├── Journal.tsx     # Journal entries
│   │   ├── Chat.tsx        # AI chat
│   │   ├── Programs.tsx    # Self-care programs
│   │   └── ...
│   ├── services/           # API services
│   │   ├── supabaseAuthService.ts
│   │   ├── supabaseDataService.ts
│   │   ├── paymentService.ts
│   │   └── ...
│   ├── types/              # TypeScript types
│   │   ├── supabase.ts     # Database types
│   │   ├── user.ts         # User types
│   │   └── ...
│   ├── App.tsx             # Main app component
│   └── main.tsx            # App entry point
├── supabase/
│   ├── schema.sql          # Database schema
│   └── functions/          # Edge Functions
│       ├── stripe-webhook/
│       ├── create-checkout/
│       └── create-portal/
├── .env.example            # Environment variables template
├── SETUP_GUIDE.md          # Setup instructions
├── ARCHITECTURE.md         # Technical documentation
└── package.json            # Dependencies
```

## 🧪 Development

### Available Scripts

```bash
# Start development server
pnpm run dev

# Build for production
pnpm run build

# Preview production build
pnpm run preview

# Run linter
pnpm run lint
```

### Code Quality

- **TypeScript** - Full type safety
- **ESLint** - Code linting
- **Prettier** - Code formatting (via ESLint)

## 🚢 Deployment

### Build

```bash
pnpm run build
```

The build output will be in the `dist/` directory.

### Deploy to Vercel

1. Push your code to GitHub
2. Import project in Vercel
3. Add environment variables
4. Deploy!

### Deploy to Netlify

1. Push your code to GitHub
2. Import project in Netlify
3. Build command: `pnpm run build`
4. Publish directory: `dist`
5. Add environment variables
6. Deploy!

## 🔐 Security

- All API keys are stored in environment variables
- Row Level Security (RLS) enabled on all database tables
- Stripe webhook signature verification
- HTTPS required in production
- Input validation with Zod schemas
- XSS protection via React's built-in escaping

## 🧩 Key Integrations

### Supabase
- **Database**: PostgreSQL with RLS
- **Authentication**: Email/password auth
- **Edge Functions**: Serverless functions for webhooks and API calls
- **Real-time**: (Optional) Live data updates

### Stripe
- **Checkout**: Hosted checkout pages
- **Subscriptions**: Recurring billing management
- **Customer Portal**: Self-service subscription management
- **Webhooks**: Automatic subscription sync

### Firebase
- **Analytics**: User behavior tracking
- **Events**: Custom event tracking
- **User Properties**: User segmentation
- **Conversion Tracking**: Purchase and engagement metrics

## 🎨 Design System

### Colors
- **Lavanda Profunda** - Primary brand color
- **Verde Esperança** - Success and positive actions
- **Amarelo Acolhedor** - Highlights and accents
- **Azul Sálvia** - Text and secondary elements
- **Offwhite** - Background

### Typography
- **Headings**: Nunito (font-heading)
- **Body**: Inter (font-sans)

### Components
All UI components are built with Shadcn/ui and fully customizable via Tailwind CSS.

## 📊 Analytics Events

The app tracks the following events:
- User registration and login
- Mood check-ins
- Journal entries
- Chat messages
- Program progress
- Appointment bookings
- Subscription purchases
- Page views

## 🐛 Troubleshooting

### App not connecting to Supabase
- Verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are correct
- Check Supabase project is active
- Ensure RLS policies are properly configured

### Stripe checkout not working
- Verify `VITE_STRIPE_PUBLISHABLE_KEY` is correct
- Check webhook endpoint is configured in Stripe Dashboard
- Ensure Edge Functions are deployed

### Firebase Analytics not tracking
- Verify all Firebase config variables are set
- Check `VITE_FIREBASE_MEASUREMENT_ID` is correct
- Wait 24-48 hours for data to appear in Firebase Console

### Build errors
```bash
# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install

# Clear Vite cache
rm -rf node_modules/.vite
pnpm run dev
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary and confidential.

## 🆘 Support

For issues or questions:
- Check [SETUP_GUIDE.md](./SETUP_GUIDE.md) for setup help
- Review [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details
- Open an issue on GitHub

## 🎯 Roadmap

- [ ] Real-time chat features
- [ ] Push notifications
- [ ] Offline support with Service Workers
- [ ] Video therapy sessions
- [ ] Multi-language support (i18n)
- [ ] Mobile apps (React Native)
- [ ] Group therapy sessions
- [ ] Meditation and breathing exercises

---

Built with ❤️ for mental health support