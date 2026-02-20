# Acollya PWA - Technical Architecture

## Overview

The Acollya PWA is a mental health application built with React, TypeScript, and Tailwind CSS. It integrates three key services:

1. **Supabase** - Backend, database, authentication, and serverless functions
2. **Stripe** - Payment processing and subscription management
3. **Firebase Analytics** - User behavior tracking and analytics

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Auth       │  │   Stripe     │  │   Firebase   │          │
│  │   Context    │  │   Provider   │  │   Analytics  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │            Application Components                 │          │
│  │  (Pages, Forms, Dashboards, Charts, etc.)       │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Services Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Supabase    │  │  Supabase    │  │   Stripe     │          │
│  │  Auth        │  │  Data        │  │   Service    │          │
│  │  Service     │  │  Service     │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Services                            │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Supabase                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │ PostgreSQL  │  │    Auth     │  │    Edge     │       │  │
│  │  │  Database   │  │   Service   │  │  Functions  │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │         │                │                  │              │  │
│  │         │                │                  ▼              │  │
│  │         │                │          ┌─────────────┐       │  │
│  │         │                │          │   Stripe    │       │  │
│  │         │                │          │   Webhook   │       │  │
│  │         │                │          └─────────────┘       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      Stripe                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │  Checkout   │  │   Customer  │  │  Webhooks   │       │  │
│  │  │   Session   │  │   Portal    │  │             │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Firebase Analytics                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │   Events    │  │    User     │  │  Dashboard  │       │  │
│  │  │  Tracking   │  │ Properties  │  │  Reporting  │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Shadcn/ui** - Component library
- **React Router** - Client-side routing
- **Zustand** - State management (legacy, being replaced by Context API)
- **React Query** - Server state management

### Backend Services
- **Supabase**
  - PostgreSQL database
  - Authentication (email/password)
  - Row Level Security (RLS)
  - Edge Functions (Deno runtime)
  - Real-time subscriptions (optional)

- **Stripe**
  - Checkout Sessions
  - Customer Portal
  - Webhooks
  - Subscription management

- **Firebase**
  - Analytics
  - Event tracking
  - User properties

## Data Flow

### Authentication Flow

```
User Registration
├─> Frontend: Register form
├─> AuthContext: signUp()
├─> Supabase Auth: Create user
├─> Supabase Trigger: Create user profile
├─> Frontend: Redirect to home
└─> Firebase: Track sign_up event

User Login
├─> Frontend: Login form
├─> AuthContext: signIn()
├─> Supabase Auth: Verify credentials
├─> Supabase: Fetch user profile
├─> Frontend: Update auth state
└─> Firebase: Track login event
```

### Subscription Flow

```
User Upgrades to Premium
├─> Frontend: Click "Upgrade" button
├─> Stripe: Create checkout session (via Edge Function)
├─> User: Redirected to Stripe Checkout
├─> User: Completes payment
├─> Stripe: Sends webhook to Supabase
├─> Edge Function: Processes webhook
├─> Supabase: Updates user plan_code
├─> Supabase: Creates subscription record
├─> Frontend: User sees premium features
└─> Firebase: Track purchase event
```

### Data Persistence Flow

```
User Creates Journal Entry
├─> Frontend: Submit journal form
├─> supabaseDataService: createJournalEntry()
├─> Supabase: Insert into journal_entries table
├─> Supabase: RLS check (user owns entry)
├─> Frontend: Show success message
└─> Firebase: Track journal_entry_created event
```

## Database Schema

### Core Tables

**users**
- Extends Supabase auth.users
- Stores user profile data
- Tracks subscription status
- Links to Stripe customer

**subscriptions**
- Tracks active subscriptions
- Synced with Stripe via webhooks
- Stores billing period info

**mood_checkins**
- Daily mood tracking
- Intensity ratings (1-5)
- Optional notes

**journal_entries**
- User journal entries
- AI-generated reflections
- Full CRUD operations

**chat_messages**
- Chat history with AI
- User and assistant messages
- Ordered by timestamp

**appointments**
- Therapy appointments
- Payment tracking
- Status management

**program_progress**
- Self-care program tracking
- Chapter completion status
- Progress timestamps

### Security

All tables use Row Level Security (RLS):
- Users can only access their own data
- Policies enforce user_id matching
- Service role key bypasses RLS for admin operations

## Edge Functions

### stripe-webhook
- **Purpose**: Handle Stripe webhook events
- **Events**: subscription.created, subscription.updated, subscription.deleted, checkout.completed
- **Actions**: Update user plan, create/update subscription records
- **Security**: Verifies webhook signature

### create-checkout
- **Purpose**: Create Stripe checkout session
- **Input**: priceId, userId
- **Output**: sessionId, checkout URL
- **Security**: Requires authentication

### create-portal
- **Purpose**: Create Stripe customer portal session
- **Input**: customerId
- **Output**: portal URL
- **Security**: Requires authentication

## State Management

### AuthContext
- Manages user authentication state
- Provides auth methods (signUp, signIn, signOut)
- Syncs with Supabase auth
- Updates Firebase Analytics user properties

### Local State
- Component-level state with useState
- Form state with react-hook-form
- Server state with React Query

### Legacy Zustand Store
- Being phased out in favor of Context API
- Currently used for backward compatibility

## Analytics Events

### User Events
- `sign_up` - User registration
- `login` - User login
- `logout` - User logout

### Feature Events
- `mood_checkin` - Mood check-in submitted
- `journal_entry_created` - Journal entry created
- `chat_message_sent` - Chat message sent
- `program_started` - Program started
- `program_completed` - Program completed
- `chapter_viewed` - Chapter viewed

### Commerce Events
- `purchase` - Subscription purchased
- `appointment_booked` - Therapy appointment booked

### Navigation Events
- `page_view` - Page viewed

## Dual Mode Support

The application supports two operational modes:

### Demo Mode
- Uses localStorage for data persistence
- Mock authentication
- No backend required
- Perfect for development and testing
- Enabled when `VITE_APP_MODE=demo` or Supabase not configured

### Production Mode
- Uses Supabase for all data operations
- Real authentication with Supabase Auth
- Stripe payment processing
- Firebase Analytics tracking
- Enabled when `VITE_APP_MODE=production` and all services configured

## Performance Optimizations

1. **Code Splitting**: React.lazy() for route-based splitting
2. **Image Optimization**: Lazy loading, responsive images
3. **Caching**: React Query for server state caching
4. **Bundle Size**: Tree shaking, dynamic imports
5. **Database**: Indexed columns, optimized queries

## Security Measures

1. **Authentication**: Supabase Auth with JWT tokens
2. **Authorization**: Row Level Security on all tables
3. **API Keys**: Environment variables, never in code
4. **Webhook Verification**: Stripe signature verification
5. **HTTPS**: Required in production
6. **Input Validation**: Zod schemas for all forms
7. **XSS Protection**: React's built-in escaping
8. **CSRF Protection**: Supabase handles this

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CDN / Edge Network                        │
│                  (Vercel, Netlify, etc.)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Static Assets                           │
│              (HTML, CSS, JS, Images)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Requests                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Supabase   │  │    Stripe    │  │   Firebase   │      │
│  │  (Database)  │  │  (Payments)  │  │ (Analytics)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring and Logging

1. **Supabase Logs**: Database queries, auth events, function executions
2. **Stripe Dashboard**: Payment events, webhook deliveries
3. **Firebase Analytics**: User behavior, conversion funnels
4. **Browser Console**: Client-side errors (in development)
5. **Error Boundaries**: React error boundaries for graceful failures

## Future Enhancements

1. **Real-time Features**: Supabase real-time subscriptions
2. **Push Notifications**: Firebase Cloud Messaging
3. **Offline Support**: Service workers, IndexedDB
4. **AI Integration**: OpenAI API for chat and reflections
5. **Video Calls**: WebRTC for therapy sessions
6. **Multi-language**: i18n support
7. **Mobile Apps**: React Native version