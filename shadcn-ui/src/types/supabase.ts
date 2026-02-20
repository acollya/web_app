export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          email: string
          name: string
          phone: string | null
          birth_date: string | null
          gender: string | null
          plan_code: number
          trial_ends_at: string | null
          subscription_status: string | null
          stripe_customer_id: string | null
          terms_accepted: boolean
          terms_accepted_date: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          email: string
          name: string
          phone?: string | null
          birth_date?: string | null
          gender?: string | null
          plan_code?: number
          trial_ends_at?: string | null
          subscription_status?: string | null
          stripe_customer_id?: string | null
          terms_accepted?: boolean
          terms_accepted_date?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          email?: string
          name?: string
          phone?: string | null
          birth_date?: string | null
          gender?: string | null
          plan_code?: number
          trial_ends_at?: string | null
          subscription_status?: string | null
          stripe_customer_id?: string | null
          terms_accepted?: boolean
          terms_accepted_date?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      subscriptions: {
        Row: {
          id: string
          user_id: string
          stripe_subscription_id: string
          stripe_price_id: string
          status: string
          current_period_start: string
          current_period_end: string
          cancel_at_period_end: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          stripe_subscription_id: string
          stripe_price_id: string
          status: string
          current_period_start: string
          current_period_end: string
          cancel_at_period_end?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          stripe_subscription_id?: string
          stripe_price_id?: string
          status?: string
          current_period_start?: string
          current_period_end?: string
          cancel_at_period_end?: boolean
          created_at?: string
          updated_at?: string
        }
      }
      mood_checkins: {
        Row: {
          id: string
          user_id: string
          mood: string
          intensity: number
          note: string | null
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          mood: string
          intensity: number
          note?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          mood?: string
          intensity?: number
          note?: string | null
          created_at?: string
        }
      }
      journal_entries: {
        Row: {
          id: string
          user_id: string
          content: string
          ai_reflection: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          content: string
          ai_reflection?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          content?: string
          ai_reflection?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      chat_messages: {
        Row: {
          id: string
          user_id: string
          role: string
          content: string
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          role: string
          content: string
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          role?: string
          content?: string
          created_at?: string
        }
      }
      appointments: {
        Row: {
          id: string
          user_id: string
          therapist_id: string
          date: string
          time: string
          status: string
          payment_status: string
          amount: number
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          therapist_id: string
          date: string
          time: string
          status?: string
          payment_status?: string
          amount: number
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          therapist_id?: string
          date?: string
          time?: string
          status?: string
          payment_status?: string
          amount?: number
          created_at?: string
          updated_at?: string
        }
      }
      program_progress: {
        Row: {
          id: string
          user_id: string
          program_id: string
          chapter_id: string
          completed: boolean
          completed_at: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          program_id: string
          chapter_id: string
          completed?: boolean
          completed_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          program_id?: string
          chapter_id?: string
          completed?: boolean
          completed_at?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      user_sessions: {
        Row: {
          id: string
          user_id: string
          session_type: string
          login_at: string
          logout_at: string | null
          user_agent: string | null
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          session_type?: string
          login_at?: string
          logout_at?: string | null
          user_agent?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          session_type?: string
          login_at?: string
          logout_at?: string | null
          user_agent?: string | null
          created_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}