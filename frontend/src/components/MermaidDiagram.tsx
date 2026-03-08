import { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

type Props = {
  chart: string;
  className?: string;
};

export function MermaidDiagram({ chart, className = '' }: Props) {
  const id = useId().replace(/:/g, '-');
  const [svg, setSvg] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const renderChart = async () => {
      try {
        const prefersDark =
          typeof window !== 'undefined' &&
          window.matchMedia('(prefers-color-scheme: dark)').matches;

        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'loose',
          theme: prefersDark ? 'dark' : 'default',
          fontFamily: 'Inter, sans-serif',
        });

        const result = await mermaid.render(`mermaid-${id}`, chart);
        if (!cancelled) {
          setSvg(result.svg);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to render diagram');
          setSvg('');
        }
      }
    };

    renderChart();

    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return (
      <div className={`rounded-3xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300 ${className}`}>
        {error}
      </div>
    );
  }

  return (
    <div
      className={`overflow-x-auto rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-4 ${className}`}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
