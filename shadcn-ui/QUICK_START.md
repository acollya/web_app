# Quick Start Guide - Acollya PWA

Get the Acollya PWA up and running in 5 minutes!

## 🚀 Option 1: Demo Mode (Fastest)

Perfect for testing and development. No backend setup required!

### Step 1: Install Dependencies

```bash
pnpm install
```

### Step 2: Run the App

```bash
pnpm run dev
```

### Step 3: Open in Browser

Navigate to `http://localhost:5173`

**That's it!** The app runs in demo mode with:
- ✅ Mock authentication
- ✅ localStorage for data persistence
- ✅ All features available
- ✅ No configuration needed

### Demo Mode Features

- Create an account (stored in localStorage)
- Track your mood daily
- Write journal entries
- Chat with AI (simulated)
- Browse self-care programs
- Book therapy appointments (simulated)
- View analytics

## 🔧 Option 2: Production Mode (Full Backend)

For production deployment with real backend services.

### Prerequisites

- Supabase account
- Stripe account
- Firebase account

### Quick Setup Steps

1. **Clone and Install**
```bash
git clone <repo-url>
cd shadcn-ui
pnpm install
```

2. **Copy Environment Template**
```bash
cp .env.example .env.local
```

3. **Set Up Supabase** (10 minutes)
   - Create project at https://supabase.com
   - Run `supabase/schema.sql` in SQL Editor
   - Copy URL and Anon Key to `.env.local`

4. **Set Up Stripe** (5 minutes)
   - Create account at https://stripe.com
   - Create products and prices
   - Copy Publishable Key to `.env.local`

5. **Set Up Firebase** (5 minutes)
   - Create project at https://firebase.google.com
   - Enable Analytics
   - Copy config to `.env.local`

6. **Update .env.local**
```env
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbG...
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
VITE_FIREBASE_API_KEY=AIza...
VITE_FIREBASE_PROJECT_ID=acollya-pwa
# ... other Firebase config
VITE_APP_MODE=production
```

7. **Run the App**
```bash
pnpm run dev
```

For detailed setup instructions, see [SETUP_GUIDE.md](./SETUP_GUIDE.md)

## 📱 Test User Flow

### 1. Registration
- Go to `/register`
- Enter email, password, and name
- Click "Criar conta"

### 2. Onboarding
- Complete the welcome flow
- Accept terms and conditions

### 3. Home Dashboard
- View your mental health dashboard
- Quick access to all features

### 4. Mood Check-in
- Click "Como você está hoje?"
- Select your mood and intensity
- Add optional notes

### 5. Journal Entry
- Navigate to Journal
- Click "Nova Entrada"
- Write your thoughts
- Get AI reflection (in production mode)

### 6. AI Chat
- Go to Chat page
- Send a message
- Receive supportive responses

### 7. Self-Care Programs
- Browse available programs
- Start a program
- Complete chapters

### 8. Therapy Appointments
- Go to Appointments
- Complete questionnaire
- Select a therapist
- Book a session

### 9. Subscription Upgrade
- Go to Profile > Manage Plan
- Click "Upgrade to Premium"
- Complete Stripe checkout (test mode)

## 🧪 Testing

### Test Stripe Payments

Use these test cards in Stripe Checkout:

| Card Number | Description |
|------------|-------------|
| 4242 4242 4242 4242 | Successful payment |
| 4000 0000 0000 0002 | Card declined |
| 4000 0025 0000 3155 | 3D Secure authentication |

- Expiry: Any future date
- CVC: Any 3 digits
- ZIP: Any 5 digits

### Test User Credentials (Demo Mode)

In demo mode, any email/password combination works!

## 🎨 Customization

### Change Colors

Edit `tailwind.config.ts`:

```typescript
colors: {
  'lavanda-profunda': '#8B5CF6',  // Primary
  'verde-esperanca': '#10B981',   // Success
  'amarelo-acolhedor': '#F59E0B', // Accent
  // ... customize as needed
}
```

### Add New Pages

1. Create page in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link if needed

### Modify Database Schema

1. Edit `supabase/schema.sql`
2. Run in Supabase SQL Editor
3. Update TypeScript types in `src/types/supabase.ts`

## 🐛 Common Issues

### Port Already in Use

```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use a different port
pnpm run dev -- --port 3000
```

### Module Not Found

```bash
# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Build Errors

```bash
# Clear Vite cache
rm -rf node_modules/.vite

# Rebuild
pnpm run build
```

### Supabase Connection Failed

- Check `.env.local` has correct values
- Verify Supabase project is active
- Ensure you're using the Anon Key (not Service Role Key)

## 📚 Next Steps

- Read [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed backend setup
- Review [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the system
- Check [README.md](./README.md) for full documentation

## 🎯 Development Workflow

```bash
# Start dev server
pnpm run dev

# In another terminal, watch for type errors
pnpm run lint

# Build for production
pnpm run build

# Preview production build
pnpm run preview
```

## 🚢 Deploy to Production

### Vercel (Recommended)

1. Push code to GitHub
2. Import project in Vercel
3. Add environment variables
4. Deploy!

### Netlify

1. Push code to GitHub
2. Import project in Netlify
3. Set build command: `pnpm run build`
4. Set publish directory: `dist`
5. Add environment variables
6. Deploy!

## ✅ Checklist

Before going to production:

- [ ] All environment variables set
- [ ] Supabase database schema deployed
- [ ] Supabase Edge Functions deployed
- [ ] Stripe products and prices created
- [ ] Stripe webhook configured
- [ ] Firebase Analytics enabled
- [ ] Terms and Privacy Policy updated
- [ ] Test payment flow end-to-end
- [ ] Test user registration and login
- [ ] Verify analytics tracking
- [ ] Run `pnpm run build` successfully
- [ ] Test production build locally with `pnpm run preview`

## 🆘 Need Help?

- 📖 Check the documentation files
- 🐛 Open an issue on GitHub
- 💬 Contact the development team

---

Happy coding! 🎉