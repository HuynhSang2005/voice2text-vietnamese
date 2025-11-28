import type { ReactNode } from 'react'
import { ConfigProvider, App } from 'antd'
import enUS from 'antd/locale/en_US'
import viVN from 'antd/locale/vi_VN'
import { defaultTheme, darkTheme, type ThemeConfig } from './antd-config'
import { useAppStore } from '@/stores/app.store'

interface AntdProviderProps {
  children: ReactNode
  locale?: 'en' | 'vi'
  theme?: ThemeConfig
}

/**
 * Ant Design Provider
 * - ConfigProvider: Global theme & locale configuration
 * - App component: Context for message, notification, modal static methods
 * 
 * Usage:
 * ```tsx
 * import { App } from 'antd'
 * 
 * function MyComponent() {
 *   const { message, notification, modal } = App.useApp()
 *   
 *   const handleClick = () => {
 *     message.success('Hello!')
 *     notification.info({ message: 'Info', description: 'Description' })
 *     modal.confirm({ title: 'Confirm?', content: 'Are you sure?' })
 *   }
 * }
 * ```
 */
export function AntdProvider({ 
  children, 
  locale = 'vi',
  theme: customTheme 
}: AntdProviderProps) {
  // Get theme preference from store if needed
  const isDarkMode = useAppStore((state) => state.isDarkMode)
  
  const currentTheme = customTheme ?? (isDarkMode ? darkTheme : defaultTheme)
  const currentLocale = locale === 'vi' ? viVN : enUS

  return (
    <ConfigProvider
      theme={currentTheme}
      locale={currentLocale}
      componentSize="middle"
    >
      <App>{children}</App>
    </ConfigProvider>
  )
}

export { App }
export type { ThemeConfig }
