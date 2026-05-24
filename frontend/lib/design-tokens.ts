/**
 * Design Tokens - Flexible Theme System
 * 
 * This file defines all design tokens including colors, spacing, typography,
 * shadows, and animations. Themes can be easily swapped by changing
 * the active theme configuration.
 */

export type ThemeName = 'royal-purple' | 'ocean-blue' | 'emerald-green' | 'sunset-orange' | 'midnight-dark'

export interface ColorTheme {
  name: ThemeName
  displayName: string
  colors: {
    primary: string
    primaryHover: string
    primaryLight: string
    primaryDark: string
    secondary: string
    secondaryHover: string
    accent: string
    success: string
    successLight: string
    warning: string
    warningLight: string
    error: string
    errorLight: string
    info: string
    infoLight: string
  }
  gradients: {
    primary: string
    success: string
    warning: string
    error: string
  }
}

export const themes: Record<ThemeName, ColorTheme> = {
  'royal-purple': {
    name: 'royal-purple',
    displayName: 'Professional Indigo',
    colors: {
      primary: '#4F46E5',
      primaryHover: '#4338CA',
      primaryLight: '#6366F1',
      primaryDark: '#3730A3',
      secondary: '#64748B',
      secondaryHover: '#475569',
      accent: '#818CF8',
      success: '#10B981',
      successLight: '#34D399',
      warning: '#F59E0B',
      warningLight: '#FBBF24',
      error: '#EF4444',
      errorLight: '#F87171',
      info: '#3B82F6',
      infoLight: '#60A5FA',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
      success: 'linear-gradient(135deg, #10B981 0%, #14B8A6 100%)',
      warning: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
      error: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
    },
  },
  'ocean-blue': {
    name: 'ocean-blue',
    displayName: 'Ocean Blue',
    colors: {
      primary: '#3B82F6',
      primaryHover: '#2563EB',
      primaryLight: '#60A5FA',
      primaryDark: '#1D4ED8',
      secondary: '#06B6D4',
      secondaryHover: '#0891B2',
      accent: '#22D3EE',
      success: '#10B981',
      successLight: '#34D399',
      warning: '#F59E0B',
      warningLight: '#FBBF24',
      error: '#EF4444',
      errorLight: '#F87171',
      info: '#6366F1',
      infoLight: '#818CF8',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%)',
      success: 'linear-gradient(135deg, #10B981 0%, #14B8A6 100%)',
      warning: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
      error: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
    },
  },
  'emerald-green': {
    name: 'emerald-green',
    displayName: 'Emerald Green',
    colors: {
      primary: '#10B981',
      primaryHover: '#059669',
      primaryLight: '#34D399',
      primaryDark: '#047857',
      secondary: '#14B8A6',
      secondaryHover: '#0D9488',
      accent: '#2DD4BF',
      success: '#10B981',
      successLight: '#34D399',
      warning: '#F59E0B',
      warningLight: '#FBBF24',
      error: '#EF4444',
      errorLight: '#F87171',
      info: '#3B82F6',
      infoLight: '#60A5FA',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #10B981 0%, #14B8A6 100%)',
      success: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
      warning: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
      error: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
    },
  },
  'sunset-orange': {
    name: 'sunset-orange',
    displayName: 'Sunset Orange',
    colors: {
      primary: '#F59E0B',
      primaryHover: '#D97706',
      primaryLight: '#FBBF24',
      primaryDark: '#B45309',
      secondary: '#EF4444',
      secondaryHover: '#DC2626',
      accent: '#FB923C',
      success: '#10B981',
      successLight: '#34D399',
      warning: '#F59E0B',
      warningLight: '#FBBF24',
      error: '#EF4444',
      errorLight: '#F87171',
      info: '#3B82F6',
      infoLight: '#60A5FA',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #F59E0B 0%, #EF4444 100%)',
      success: 'linear-gradient(135deg, #10B981 0%, #14B8A6 100%)',
      warning: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
      error: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
    },
  },
  'midnight-dark': {
    name: 'midnight-dark',
    displayName: 'Midnight Dark',
    colors: {
      primary: '#8B5CF6',
      primaryHover: '#7C3AED',
      primaryLight: '#A78BFA',
      primaryDark: '#6D28D9',
      secondary: '#6366F1',
      secondaryHover: '#4F46E5',
      accent: '#A78BFA',
      success: '#10B981',
      successLight: '#34D399',
      warning: '#F59E0B',
      warningLight: '#FBBF24',
      error: '#EF4444',
      errorLight: '#F87171',
      info: '#3B82F6',
      infoLight: '#60A5FA',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%)',
      success: 'linear-gradient(135deg, #10B981 0%, #14B8A6 100%)',
      warning: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
      error: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
    },
  },
}

// Spacing scale (4px base unit)
export const spacing = {
  0: '0',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
} as const

// Border radius scale
export const borderRadius = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
} as const

// Typography scale
export const typography = {
  fontFamily: {
    sans: "'Inter', system-ui, sans-serif",
    mono: "'JetBrains Mono', monospace",
  },
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '30px',
    '4xl': '36px',
    '5xl': '48px',
  },
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
} as const

// Shadow scale
export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  md: '0 2px 8px rgba(0, 0, 0, 0.08)',
  lg: '0 4px 16px rgba(0, 0, 0, 0.1)',
  xl: '0 12px 32px rgba(0, 0, 0, 0.12)',
  '2xl': '0 24px 48px rgba(0, 0, 0, 0.15)',
  inner: 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',
  none: 'none',
} as const

// Animation durations
export const animations = {
  fast: '150ms',
  normal: '300ms',
  slow: '500ms',
  slower: '750ms',
} as const

// Z-index scale
export const zIndex = {
  base: 0,
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
} as const

// Breakpoints (for reference, Tailwind handles these)
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const

// Get active theme
export function getTheme(themeName: ThemeName = 'royal-purple'): ColorTheme {
  return themes[themeName]
}

// Get all available themes
export function getAllThemes(): ColorTheme[] {
  return Object.values(themes)
}

// Default theme
export const defaultTheme: ThemeName = 'royal-purple'
