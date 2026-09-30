import { useEffect, useState } from 'react'

import { applyTheme, getInitialTheme, type Theme } from '../lib/theme'

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const toggle = () => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))

  return [theme, toggle]
}
