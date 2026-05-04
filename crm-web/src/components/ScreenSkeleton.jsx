const PULSE_KEYFRAMES = `
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
`;

const skeletonBlock = {
  background: 'var(--surface-panel-elevated)',
  borderRadius: 'var(--radius-md)',
  animation: 'pulse 1.4s ease-in-out infinite',
};

export function ScreenSkeleton({ variant = 'table' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <style>{PULSE_KEYFRAMES}</style>
      {variant === 'dashboard' && <DashboardSkeleton />}
      {variant === 'table' && <TableSkeleton />}
      {variant === 'card' && <CardSkeleton />}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ ...skeletonBlock, height: 88 }} />
        ))}
      </div>
      <div style={{ ...skeletonBlock, height: 220 }} />
      <div style={{ ...skeletonBlock, height: 180 }} />
    </>
  );
}

function TableSkeleton() {
  return (
    <>
      <div style={{ ...skeletonBlock, height: 36 }} />
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} style={{ ...skeletonBlock, height: 44, opacity: 0.6 }} />
      ))}
    </>
  );
}

function CardSkeleton() {
  return (
    <>
      <div style={{ ...skeletonBlock, height: 80 }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ ...skeletonBlock, height: 88 }} />
        ))}
      </div>
      <div style={{ ...skeletonBlock, height: 220 }} />
    </>
  );
}

export default ScreenSkeleton;
