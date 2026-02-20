export interface JournalEntry {
  id: string;
  userId: string;
  content: string;
  audioUrl?: string;
  createdAt: string;
  aiReflection?: string;
}

export interface JournalReflectionRequest {
  entryId: string;
  content: string;
}