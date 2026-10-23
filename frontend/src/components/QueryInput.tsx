import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, CornerDownLeft, ShieldAlert, Loader2 } from 'lucide-react';

interface QueryInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  initialQuestion?: string;
}

const EXAMPLE_QUERIES = [
  { text: 'How many orders did we receive this month?', tag: 'Orders' },
  { text: 'What is our total revenue?', tag: 'Revenue' },
  { text: 'Show the top 5 customers by total spending.', tag: 'Customers' },
  { text: 'Compare monthly sales.', tag: 'Analytics' },
  { text: 'How many orders were placed last week?', tag: 'Recent' },
  { text: 'DROP TABLE customers; SELECT * FROM products;', tag: 'Security Test', isDangerous: true },
];

export const QueryInput: React.FC<QueryInputProps> = ({
  onSubmit,
  isLoading,
  initialQuestion = '',
}) => {
  const [question, setQuestion] = useState(initialQuestion);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialQuestion) {
      setQuestion(initialQuestion);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [initialQuestion]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const selectExample = (exampleText: string) => {
    setQuestion(exampleText);
    onSubmit(exampleText);
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4">
      {/* Input container card */}
      <div className="relative bg-white rounded-2xl border border-slate-200/90 shadow-sm shadow-slate-200/50 hover:border-slate-300 transition-all focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500">
        <form onSubmit={handleSubmit} className="p-4">
          <div className="flex items-start space-x-3">
            <div className="pt-2 text-indigo-500">
              <Sparkles className="w-5 h-5" />
            </div>
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Ask your data anything (e.g. Which product generated the highest revenue?)"
              className="w-full resize-none bg-transparent text-slate-800 placeholder-slate-400 focus:outline-none text-base leading-relaxed"
              disabled={isLoading}
            />
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2 text-[11px] text-slate-400 select-none">
              <span className="flex items-center space-x-1 font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 border border-slate-200">
                <CornerDownLeft className="w-3 h-3 inline" /> Enter
              </span>
              <span>to send</span>
              <span>•</span>
              <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 border border-slate-200">
                Shift + Enter
              </span>
              <span>for new line</span>
            </div>

            <button
              type="submit"
              disabled={isLoading || !question.trim()}
              className={`flex items-center space-x-2 px-5 py-2 rounded-xl text-sm font-semibold transition-all shadow-sm ${
                isLoading || !question.trim()
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20 active:scale-95'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <span>Run Query</span>
                  <Send className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Suggested question chips */}
      <div className="space-y-1.5">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center space-x-1 px-1">
          <span>Try an example</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((ex, idx) => (
            <button
              key={idx}
              onClick={() => selectExample(ex.text)}
              disabled={isLoading}
              className={`text-xs px-3 py-1.5 rounded-lg border text-left transition-all flex items-center space-x-2 ${
                ex.isDangerous
                  ? 'bg-rose-50/70 border-rose-200 text-rose-700 hover:bg-rose-100 hover:border-rose-300'
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-indigo-300 hover:text-indigo-600 shadow-xs'
              }`}
            >
              {ex.isDangerous ? (
                <ShieldAlert className="w-3.5 h-3.5 text-rose-500 shrink-0" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
              )}
              <span className="truncate max-w-xs">{ex.text}</span>
              <span
                className={`text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded ${
                  ex.isDangerous ? 'bg-rose-200/60 text-rose-800' : 'bg-slate-100 text-slate-500'
                }`}
              >
                {ex.tag}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
