'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { type ThemeName, getTheme, defaultTheme, themes } from './design-tokens'

interface ThemeContextType {
  theme: ThemeName
  themeColors: ReturnType<typeof getTheme>
  setTheme: (theme: ThemeName) => void
  availableThemes: typeof themes
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const THEME_STORAGE_KEY = 'resumeranker-theme'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(defaultTheme)
  const [mounted, setMounted] = useState(false)

  // Load theme from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY) as ThemeName | null
    if (stored && stored in themes) {
      setThemeState(stored)
    }
    setMounted(true)
  }, [])

  // Apply theme to document root
  useEffect(() => {
    if (!mounted) return

    const themeColors = getTheme(theme)
    const root = document.documentElement

    // Apply CSS custom properties
    root.style.setProperty('--color-primary', themeColors.colors.primary)
    root.style.setProperty('--color-primary-hover', themeColors.colors.primaryHover)
    root.style.setProperty('--color-primary-light', themeColors.colors.primaryLight)
    root.style.setProperty('--color-primary-dark', themeColors.colors.primaryDark)
    root.style.setProperty('--color-secondary', themeColors.colors.secondary)
    root.style.setProperty('--color-secondary-hover', themeColors.colors.secondaryHover)
    root.style.setProperty('--color-accent', themeColors.colors.accent)
    root.style.setProperty('--color-success', themeColors.colors.success)
    root.style.setProperty('--color-success-light', themeColors.colors.successLight)
    root.style.setProperty('--color-warning', themeColors.colors.warning)
    root.style.setProperty('--color-warning-light', themeColors.colors.warningLight)
    root.style.setProperty('--color-error', themeColors.colors.error)
    root.style.setProperty('--color-error-light', themeColors.colors.errorLight)
    root.style.setProperty('--color-info', themeColors.colors.info)
    root.style.setProperty('--color-info-light', themeColors.colors.infoLight)
    root.style.setProperty('--gradient-primary', themeColors.gradients.primary)
    root.style.setProperty('--gradient-success', themeColors.gradients.success)
    root.style.setProperty('--gradient-warning', themeColors.gradients.warning)
    root.style.setProperty('--gradient-error', themeColors.gradients.error)

    // Add theme class to html element
    root.classList.remove(...Object.keys(themes).map(t => `theme-${t}`))
    root.classList.add(`theme-${theme}`)
  }, [theme, mounted])

  const setTheme = useCallback((newTheme: ThemeName) => {
    setThemeState(newTheme)
    localStorage.setItem(THEME_STORAGE_KEY, newTheme)
  }, [])

  const value: ThemeContextType = {
    theme,
    themeColors: getTheme(theme),
    setTheme,
    availableThemes: themes,
  }

  // Prevent flash of unstyled content
  if (!mounted) {
    return <>{children}</>
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
