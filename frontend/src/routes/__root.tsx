import { createRootRoute, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { Layout } from 'antd'

const { Content } = Layout

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <Layout className="min-h-screen">
      <Content>
        <Outlet />
      </Content>
      <TanStackRouterDevtools />
    </Layout>
  )
}
