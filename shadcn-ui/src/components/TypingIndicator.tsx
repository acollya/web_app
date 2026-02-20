export function TypingIndicator() {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div className="bg-lavanda-serenidade rounded-[18px] px-6 py-4 shadow-sm">
        <div className="flex gap-1.5">
          <div className="w-2 h-2 bg-azul-salvia rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-azul-salvia rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-azul-salvia rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}