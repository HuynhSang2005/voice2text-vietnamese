import { createFileRoute } from '@tanstack/react-router'
import { Typography, Button, Space, Card, App, Select, Switch, Flex } from 'antd'
import { AudioOutlined, SunOutlined, MoonOutlined } from '@ant-design/icons'
import { useAppStore } from '@/stores/app.store'

const { Title, Text, Paragraph } = Typography

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  const { message, notification } = App.useApp()
  
  const {
    selectedModel,
    setSelectedModel,
    isDarkMode,
    toggleDarkMode,
  } = useAppStore()

  const handleTestMessage = () => {
    message.success('Ant Design đã được cấu hình thành công!')
  }

  const handleTestNotification = () => {
    notification.info({
      title: 'Thông báo',
      description: 'Voice to Text - Vietnamese Speech Recognition đã sẵn sàng!',
      placement: 'topRight',
    })
  }

  return (
    <main className="p-8">
      <Card className="max-w-2xl mx-auto">
        <Flex vertical gap="middle" align="center">
          <AudioOutlined style={{ fontSize: 48, color: '#1677ff' }} />
          
          <Title level={2} className="!mb-0">Voice to Text</Title>
          <Text type="secondary">Vietnamese Speech Recognition</Text>
          
          <Paragraph className="text-center">
            Chuyển đổi giọng nói tiếng Việt thành văn bản với độ chính xác cao.
          </Paragraph>

          <Space direction="vertical" size="middle" className="w-full max-w-xs">
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              options={[
                { value: 'zipformer', label: 'Zipformer (Nhanh)' },
                { value: 'faster-whisper', label: 'Faster Whisper' },
                { value: 'phowhisper', label: 'PhoWhisper' },
                { value: 'hkab', label: 'HKAB' },
              ]}
              className="w-full"
              placeholder="Chọn model"
            />

            <Space>
              <Button type="primary" onClick={handleTestMessage}>
                Test Message
              </Button>
              <Button onClick={handleTestNotification}>
                Test Notification
              </Button>
            </Space>

            <Flex align="center" gap="small" justify="center">
              <SunOutlined />
              <Switch
                checked={isDarkMode}
                onChange={toggleDarkMode}
              />
              <MoonOutlined />
            </Flex>
          </Space>
        </Flex>
      </Card>
    </main>
  )
}
