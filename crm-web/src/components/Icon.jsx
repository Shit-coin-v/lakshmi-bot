import * as Lucide from 'lucide-react';

const toComponentName = (kebab) =>
  kebab
    .split('-')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join('');

export function Icon({ name, size = 18, strokeWidth = 1.75, style }) {
  const Cmp = Lucide[toComponentName(name)];
  if (!Cmp) {
    return <span style={{ display: 'inline-block', width: size, height: size, ...style }} aria-hidden />;
  }
  return <Cmp size={size} strokeWidth={strokeWidth} style={style} aria-hidden />;
}

export default Icon;
