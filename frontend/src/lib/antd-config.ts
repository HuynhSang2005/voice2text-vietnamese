import type { ThemeConfig } from 'antd'
import { theme } from 'antd'

// Re-export ThemeConfig for use in other files
export type { ThemeConfig }

/**
 * Ant Design 6.0 Theme Configuration
 * - CSS-in-JS with design tokens
 * - Dark/Light mode support via algorithm
 * - Component-level customization
 */

// Light theme configuration
export const lightTheme: ThemeConfig = {
  token: {
    // Primary color - customize as needed
    colorPrimary: '#1677ff',
    
    // Border radius
    borderRadius: 6,
    
    // Font settings
    fontSize: 14,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
    
    // Control height
    controlHeight: 32,
  },
  components: {
    Button: {
      algorithm: true, // Enable algorithm for derived colors
    },
    Input: {
      algorithm: true,
    },
    Select: {
      algorithm: true,
    },
  },
}

// Dark theme configuration
export const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    fontSize: 14,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
    controlHeight: 32,
  },
  components: {
    Button: {
      algorithm: true,
    },
    Input: {
      algorithm: true,
    },
    Select: {
      algorithm: true,
    },
  },
}

// Compact theme (can be combined with dark)
export const compactTheme: ThemeConfig = {
  algorithm: theme.compactAlgorithm,
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 4,
  },
}

// Export default theme
export const defaultTheme = lightTheme
