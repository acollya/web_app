export interface Program {
  id: string;
  title: string;
  description: string;
  category: string;
  coverImage: string;
  isPremium: boolean;
  price?: number;
  totalChapters: number;
  completedChapters?: number;
}

export interface Chapter {
  id: string;
  programId: string;
  chapterNumber: number;
  title: string;
  contentType: 'pdf' | 'video';
  contentUrl: string;
  duration?: number; // in minutes, for videos
  isCompleted: boolean;
}

export interface ChapterContent {
  id: string;
  chapterId: string;
  type: 'pdf' | 'video';
  url: string;
  metadata?: {
    duration?: number;
    pages?: number;
    size?: string;
  };
}

export interface ProgramProgress {
  id: string;
  userId: string;
  programId: string;
  completedChapters: string[];
  currentChapter?: string;
  lastAccessedAt: string;
  status: 'not-started' | 'in-progress' | 'completed';
}