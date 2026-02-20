import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { programService } from '@/services/programService';
import { Program, Chapter } from '@/types/program';
import { useToast } from '@/hooks/use-toast';
import { Play, CheckCircle2, Lock, FileText, Video } from 'lucide-react';

export default function ProgramDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [program, setProgram] = useState<Program | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadProgramData();
  }, [id]);

  const loadProgramData = async () => {
    if (!id) return;
    
    try {
      const [programData, chaptersData] = await Promise.all([
        programService.getProgram(id),
        programService.getChapters(id),
      ]);
      setProgram(programData);
      setChapters(chaptersData);
    } catch (error) {
      toast({
        title: 'Erro ao carregar programa',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
      navigate('/programs');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChapterClick = (chapter: Chapter) => {
    navigate(`/programs/${id}/chapter/${chapter.id}`);
  };

  if (isLoading || !program) {
    return (
      <div className="min-h-screen bg-offwhite flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const progressPercentage = program.totalChapters > 0
    ? ((program.completedChapters || 0) / program.totalChapters) * 100
    : 0;

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title={program.title} showBack />
      
      <div className="max-w-2xl mx-auto">
        {/* Program Header */}
        <div className="relative">
          <img
            src={program.coverImage}
            alt={program.title}
            className="w-full h-56 object-cover bg-lavanda-serenidade"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          
          <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
            <span className="px-3 py-1 bg-white/20 backdrop-blur-sm text-white text-xs rounded-full font-medium mb-2 inline-block">
              {program.category}
            </span>
            <h1 className="text-2xl font-heading font-bold mb-2">
              {program.title}
            </h1>
            <p className="text-sm text-white/90">
              {program.description}
            </p>
          </div>
        </div>

        {/* Progress */}
        {progressPercentage > 0 && (
          <div className="px-6 py-4 bg-white border-b border-cinza-neutro/30">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-azul-salvia">
                    Seu Progresso
                  </span>
                  <span className="text-sm font-bold text-lavanda-profunda">
                    {Math.round(progressPercentage)}%
                  </span>
                </div>
                <div className="h-2 bg-cinza-neutro/20 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-verde-esperanca transition-all"
                    style={{ width: `${progressPercentage}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Chapters List */}
        <div className="px-6 py-6">
          <h2 className="text-lg font-heading font-bold text-azul-salvia mb-4">
            Capítulos
          </h2>
          
          <div className="space-y-3">
            {chapters.map((chapter) => (
              <button
                key={chapter.id}
                onClick={() => handleChapterClick(chapter)}
                className="w-full bg-white rounded-xl p-4 text-left hover:shadow-md transition-shadow border border-cinza-neutro/30"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                    chapter.isCompleted
                      ? 'bg-verde-esperanca text-white'
                      : 'bg-lavanda-serenidade text-lavanda-profunda'
                  }`}>
                    {chapter.isCompleted ? (
                      <CheckCircle2 className="w-6 h-6" />
                    ) : (
                      <span className="font-bold">{chapter.chapterNumber}</span>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-azul-salvia mb-1">
                      {chapter.title}
                    </h3>
                    <div className="flex items-center gap-2 text-xs text-azul-salvia/60">
                      {chapter.contentType === 'video' ? (
                        <>
                          <Video className="w-3 h-3" />
                          <span>Vídeo</span>
                          {chapter.duration && <span>• {chapter.duration} min</span>}
                        </>
                      ) : (
                        <>
                          <FileText className="w-3 h-3" />
                          <span>Leitura</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex-shrink-0">
                    {chapter.isCompleted ? (
                      <span className="text-xs text-verde-esperanca font-medium">
                        Concluído
                      </span>
                    ) : (
                      <Play className="w-5 h-5 text-lavanda-profunda" />
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}