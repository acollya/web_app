import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { programService } from '@/services/programService';
import { Chapter } from '@/types/program';
import { useToast } from '@/hooks/use-toast';
import ReactPlayer from 'react-player';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import '@react-pdf-viewer/core/lib/styles/index.css';
import { CheckCircle2 } from 'lucide-react';

export default function ChapterView() {
  const { programId, chapterId } = useParams<{ programId: string; chapterId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCompleting, setIsCompleting] = useState(false);

  useEffect(() => {
    loadChapter();
  }, [programId, chapterId]);

  const loadChapter = async () => {
    if (!programId || !chapterId) return;
    
    try {
      const data = await programService.getChapter(programId, chapterId);
      setChapter(data);
    } catch (error) {
      toast({
        title: 'Erro ao carregar capítulo',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
      navigate(`/programs/${programId}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!programId || !chapterId) return;
    
    setIsCompleting(true);
    try {
      await programService.completeChapter(programId, chapterId);
      toast({
        title: 'Capítulo concluído!',
        description: 'Continue seu progresso no próximo capítulo',
      });
      navigate(`/programs/${programId}`);
    } catch (error) {
      toast({
        title: 'Erro ao marcar como concluído',
        description: 'Tente novamente',
        variant: 'destructive',
      });
    } finally {
      setIsCompleting(false);
    }
  };

  if (isLoading || !chapter) {
    return (
      <div className="min-h-screen bg-offwhite flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader 
        title={`Capítulo ${chapter.chapterNumber}: ${chapter.title}`} 
        showBack 
      />
      
      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Content */}
        <div className="bg-white rounded-2xl overflow-hidden shadow-sm mb-6">
          {chapter.contentType === 'video' ? (
            <div className="aspect-video bg-black">
              <ReactPlayer
                url={chapter.contentUrl}
                width="100%"
                height="100%"
                controls
                playing={false}
                config={{
                  youtube: {
                    playerVars: { showinfo: 1 }
                  }
                }}
              />
            </div>
          ) : (
            <div className="h-[600px]">
              <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                <Viewer fileUrl={chapter.contentUrl} />
              </Worker>
            </div>
          )}
        </div>

        {/* Complete Button */}
        {!chapter.isCompleted && (
          <div className="bg-white rounded-2xl p-6">
            <div className="text-center mb-4">
              <h3 className="font-heading font-bold text-lg text-azul-salvia mb-2">
                Finalizou este capítulo?
              </h3>
              <p className="text-sm text-azul-salvia/70">
                Marque como concluído para acompanhar seu progresso
              </p>
            </div>
            
            <Button
              onClick={handleComplete}
              disabled={isCompleting}
              className="w-full h-14 bg-verde-esperanca hover:bg-verde-esperanca/90 text-white rounded-xl text-lg font-semibold"
            >
              <CheckCircle2 className="w-5 h-5 mr-2" />
              {isCompleting ? 'Salvando...' : 'Marcar como Concluído'}
            </Button>
          </div>
        )}

        {chapter.isCompleted && (
          <div className="bg-verde-esperanca/10 border border-verde-esperanca/30 rounded-xl p-4 text-center">
            <CheckCircle2 className="w-8 h-8 text-verde-esperanca mx-auto mb-2" />
            <p className="font-semibold text-verde-esperanca">
              Capítulo Concluído!
            </p>
            <p className="text-sm text-azul-salvia/70 mt-1">
              Continue seu progresso no próximo capítulo
            </p>
          </div>
        )}
      </div>
    </div>
  );
}