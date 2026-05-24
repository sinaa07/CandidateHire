'use client'

import React, { useState } from 'react'
import { Palette, Check, ChevronDown } from 'lucide-react'
import { useTheme } from '@/lib/theme-context'
import { type ThemeName } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export function ThemeSwitcher() {
  const { theme, setTheme, availableThemes } = useTheme()
  const [open, setOpen] = useState(false)

  const currentTheme = availableThemes[theme]

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          aria-label="Change theme"
        >
          <Palette className="h-4 w-4" />
          <span className="hidden sm:inline">{currentTheme.displayName}</span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Choose Theme</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {Object.values(availableThemes).map((themeOption) => (
          <DropdownMenuItem
            key={themeOption.name}
            onClick={() => {
              setTheme(themeOption.name)
              setOpen(false)
            }}
            className="flex items-center justify-between cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full border-2 border-border"
                style={{ backgroundColor: themeOption.colors.primary }}
              />
              <span>{themeOption.displayName}</span>
            </div>
            {theme === themeOption.name && (
              <Check className="h-4 w-4 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// Compact version for mobile/small spaces
export function ThemeSwitcherCompact() {
  const { theme, setTheme, availableThemes } = useTheme()
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9"
          aria-label="Change theme"
        >
          <Palette className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Choose Theme</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {Object.values(availableThemes).map((themeOption) => (
          <DropdownMenuItem
            key={themeOption.name}
            onClick={() => {
              setTheme(themeOption.name)
              setOpen(false)
            }}
            className="flex items-center justify-between cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full border-2 border-border"
                style={{ backgroundColor: themeOption.colors.primary }}
              />
              <span>{themeOption.displayName}</span>
            </div>
            {theme === themeOption.name && (
              <Check className="h-4 w-4 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
