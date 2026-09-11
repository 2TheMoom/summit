/**
 * Summit Logo Component
 *
 * "Peak & Flag" mark: a mountain outline with a flag planted at the summit -
 * whoever the flag represents is currently #1, live.
 *
 * Variants:
 * - "full": Mark + Wordmark (for desktop/larger spaces)
 * - "mark": Mark only (for mobile/compact spaces)
 * - "wordmark": Wordmark only
 */

import React from 'react';

export type LogoVariant = 'full' | 'mark' | 'wordmark';
export type LogoSize = 'sm' | 'md' | 'lg';
export type LogoTheme = 'light' | 'dark';

interface LogoProps {
  variant?: LogoVariant;
  size?: LogoSize;
  theme?: LogoTheme;
  className?: string;
}

const sizeMap = {
  sm: { mark: 'w-5 h-5', text: 'text-base' },
  md: { mark: 'w-6 h-6', text: 'text-xl' },
  lg: { mark: 'w-8 h-8', text: 'text-2xl' },
};

export function Logo({
  variant = 'full',
  size = 'md',
  theme = 'dark',
  className = '',
}: LogoProps) {
  const colorClass = theme === 'dark' ? 'text-foreground' : 'text-background';
  const { mark: markSize, text: textSize } = sizeMap[size];

  const PeakMark = () => (
    <svg
      className={`${markSize} transition-colors`}
      viewBox="0 0 40 40"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Summit Logo"
    >
      <path
        d="M20 6 L33 30 H7 Z"
        fill="none"
        stroke="var(--primary)"
        strokeWidth="2.4"
        strokeLinejoin="round"
      />
      <path d="M20 6 L20 16.5 L26 13.7 Z" fill="var(--flag)" />
    </svg>
  );

  const Wordmark = () => (
    <span
      className={`${textSize} font-bold ${colorClass} font-[family-name:var(--font-display)] transition-colors`}
      style={{ letterSpacing: '-0.01em' }}
    >
      Summit
    </span>
  );

  if (variant === 'mark') {
    return (
      <div className={`inline-flex items-center ${className}`}>
        <PeakMark />
      </div>
    );
  }

  if (variant === 'wordmark') {
    return (
      <div className={`inline-flex items-center ${className}`}>
        <Wordmark />
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <PeakMark />
      <Wordmark />
    </div>
  );
}

export function LogoFull(props: Omit<LogoProps, 'variant'>) {
  return <Logo {...props} variant="full" />;
}

export function LogoMark(props: Omit<LogoProps, 'variant'>) {
  return <Logo {...props} variant="mark" />;
}

export function LogoWordmark(props: Omit<LogoProps, 'variant'>) {
  return <Logo {...props} variant="wordmark" />;
}
