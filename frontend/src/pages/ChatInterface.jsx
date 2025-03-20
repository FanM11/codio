import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, Avatar, message, Spin, Typography } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined, LoadingOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Text } = Typography;

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const [placeholder, setPlaceholder] = useState('输入您的问题，例如："我想订从北京到上海的机票"');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Create session ID on component mount
    if (!sessionId) {
      const newSessionId = `session_${Date.now()}`;
      setSessionId(newSessionId);
      console.log('Created new session:', newSessionId);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
    if (messages.length === 0) {
      setMessages([{
        type: 'bot',
        content: '您好！我是您的机票预订助手。请问您想预订从哪里到哪里的机票？',
        time: new Date()
      }]);
    }
  }, [messages]);

  const sendPredefinedMessage = (message) => {
    // 设置输入文本
    setInputText(message);

    // 使用setTimeout确保状态更新后再触发发送
    setTimeout(() => {
      handleSend();
    }, 100);
  };

  const handleSend = async () => {
    const messageToSend = inputText.trim();
    if (!messageToSend) return;
    if (!sessionId) {
      message.error('会话未初始化，请刷新页面。');
      return;
    }

    const userMessage = {
      type: 'user',
      content: messageToSend,
      time: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLoading(true);

    try {
      // 显示用户输入后立即显示一个加载状态
      setMessages(prev => [...prev, {
        type: 'bot',
        content: <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />,
        time: new Date(),
        isLoading: true
      }]);

      const response = await axios.post('http://localhost:8000/api/chat/', {
        message: messageToSend,
        session_id: sessionId
      });

      // 移除加载状态消息
      setMessages(prev => prev.filter(msg => !msg.isLoading));

      const botMessage = {
        type: 'bot',
        content: response.data.message,
        time: new Date()
      };

      setMessages(prev => [...prev, botMessage]);

      // 根据回复内容更新输入提示
      if (response.data.message.includes('请选择航班号')) {
        setPlaceholder('请输入航班选项编号，例如："1"');
      } else if (response.data.message.includes('请提供以下信息')) {
        setPlaceholder('请输入您的联系信息，例如："我的名字是张三，电话13800138000，邮箱example@email.com"');
      } else if (response.data.message.includes('请确认您的订单信息')) {
        setPlaceholder('输入"确认"完成预订，或输入"修改"更改信息');
      } else if (response.data.message.includes('请告诉我您想修改的信息')) {
        setPlaceholder('请提供您想修改的信息，或输入"确认"完成');
      } else {
        setPlaceholder('输入您的问题，例如："我想订从北京到上海的机票"');
      }
    } catch (error) {
      console.error('Chat error:', error);
      message.error('消息发送失败，请重试。');

      // 移除加载状态消息
      setMessages(prev => prev.filter(msg => !msg.isLoading));

      // 添加错误提示
      setMessages(prev => [...prev, {
        type: 'bot',
        content: '抱歉，服务暂时不可用，请稍后再试。',
        time: new Date(),
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const renderFlightInfo = (content) => {
    if (typeof content !== 'string') return content;

    // 处理航班信息格式化
    if (content.includes('航班选项') && content.includes('请选择航班号')) {
      const sections = content.split(/(?=航班选项 \d+:)/);

      return (
        <div>
          {sections[0].trim() && <p>{sections[0]}</p>}
          <div style={{ backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '8px', marginBottom: '10px' }}>
            {sections.slice(1).map((section, index) => (
              <div key={index} style={{
                padding: '8px',
                margin: '5px 0',
                backgroundColor: 'white',
                borderRadius: '5px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                {section.split('\n').map((line, lineIndex) => (
                  <div key={lineIndex} style={{ marginBottom: '3px' }}>
                    {line.includes('价格') ?
                      <Text strong style={{ color: '#ff4d4f' }}>{line}</Text> :
                      <Text>{line}</Text>}
                  </div>
                ))}
              </div>
            ))}
          </div>
          <p>{content.split('\n\n').pop()}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
            {[1, 2, 3, 4, 5].map(num => (
              <Button
                key={num}
                size="small"
                onClick={() => sendPredefinedMessage(String(num))}
              >
                选择航班 {num}
              </Button>
            ))}
          </div>
        </div>
      );
    }

    // 处理订单确认信息
    if (content.includes('请确认您的订单信息')) {
      const sections = content.split('\n\n');
      const header = sections[0];

      // 找到航班信息和乘客信息部分
      let flightInfoSection = [];
      let passengerInfoSection = [];

      // 检测每个部分的内容
      sections.forEach(section => {
        if (section.startsWith('航班信息')) {
          flightInfoSection = section.split('\n');
        } else if (section.startsWith('乘客信息')) {
          passengerInfoSection = section.split('\n');
        }
      });

      // 如果没有找到特定格式，使用旧的解析方法
      if (flightInfoSection.length === 0) {
        // 老的解析方式
        const flightInfo = sections[1]?.split('\n') || [];
        const passengerInfo = sections[2]?.split('\n') || [];
        flightInfoSection = flightInfo;
        passengerInfoSection = passengerInfo;
      }

      const footer = sections[sections.length - 1] || '';

      return (
        <div>
          <p>{header}</p>
          <div style={{
            backgroundColor: '#f0f8ff',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '10px',
            border: '1px solid #91d5ff'
          }}>
            <div style={{ marginBottom: '8px' }}>
              <Text strong style={{ display: 'block', marginBottom: '5px' }}>航班信息</Text>
              {flightInfoSection.map((line, index) => {
                // 跳过"航班信息"标题行
                if (line === '航班信息' || !line.trim()) return null;
                return <div key={index}>{line}</div>;
              })}
            </div>
            <div>
              <Text strong style={{ display: 'block', marginBottom: '5px' }}>乘客信息</Text>
              {passengerInfoSection.map((line, index) => {
                // 跳过"乘客信息"标题行
                if (line === '乘客信息' || !line.trim()) return null;
                return <div key={index}>{line}</div>;
              })}
            </div>
          </div>
          <p>{footer}</p>

          {/* 添加确认和修改按钮 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px' }}>
            <Button
              type="primary"
              onClick={() => sendPredefinedMessage('确认')}
            >
              确认预订
            </Button>
            <Button
              onClick={() => sendPredefinedMessage('修改')}
            >
              修改信息
            </Button>
          </div>
        </div>
      );
    }

    // 处理修改信息屏幕
    if (content.includes('请告诉我您想修改的信息') && content.includes('完成修改后')) {
      const lines = content.split('\n');
      const header = lines[0];

      // 将内容分为信息部分和指南部分
      const infoEndIndex = lines.findIndex(line => line.includes('您可以通过以下方式修改信息'));
      const currentInfo = lines.slice(1, infoEndIndex).join('\n');
      const guidanceInfo = lines.slice(infoEndIndex).join('\n');

      return (
        <div>
          <p>{header}</p>
          <div style={{
            backgroundColor: '#fff1f0',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '10px',
            border: '1px solid #ffa39e'
          }}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{currentInfo}</pre>
          </div>
          <div style={{
            backgroundColor: '#f6ffed',
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid #b7eb8f'
          }}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{guidanceInfo}</pre>
          </div>

          {/* 快速操作按钮 */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
            <Button size="small" onClick={() => sendPredefinedMessage('重新选择航班')}>
              重选航班
            </Button>
            <Button size="small" onClick={() => sendPredefinedMessage('确认')}>
              完成修改
            </Button>
          </div>
        </div>
      );
    }

    // 处理预订成功消息
    if (content.includes('预订成功')) {
      return (
        <div style={{
          backgroundColor: '#f6ffed',
          padding: '12px',
          borderRadius: '8px',
          border: '1px solid #b7eb8f'
        }}>
          {content.split('\n').map((line, index) => (
            <p key={index}>{line}</p>
          ))}
        </div>
      );
    }

    // 对于普通文本，保留换行
    return content.split('\n').map((line, index) => (
      <div key={index} style={{ marginBottom: '5px' }}>{line}</div>
    ));
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <RobotOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
            <span>智能机票预订助手</span>
          </div>
        }
        extra={
          sessionId && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              会话ID: {sessionId}
            </Text>
          )
        }
      >
        {/* Chat Messages Area */}
        <div
          style={{
            height: '500px',
            overflowY: 'auto',
            marginBottom: '20px',
            padding: '10px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px'
          }}
        >
          {messages.map((msg, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                justifyContent: msg.type === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: '15px'
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  maxWidth: '80%'
                }}
              >
                {msg.type === 'bot' && (
                  <Avatar
                    icon={<RobotOutlined />}
                    style={{
                      backgroundColor: msg.isError ? '#ff4d4f' : '#1890ff',
                      marginRight: '8px',
                      marginTop: '4px'
                    }}
                  />
                )}
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: '12px',
                    backgroundColor: msg.type === 'user' ? '#1890ff' : 'white',
                    color: msg.type === 'user' ? 'white' : 'black',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                  }}
                >
                  {renderFlightInfo(msg.content)}
                </div>
                {msg.type === 'user' && (
                  <Avatar
                    icon={<UserOutlined />}
                    style={{
                      backgroundColor: '#1890ff',
                      marginLeft: '8px',
                      marginTop: '4px'
                    }}
                  />
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <Input
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onPressEnter={handleSend}
            placeholder={placeholder}
            disabled={loading}
            style={{ padding: '10px 15px' }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            size="large"
          >
            发送
          </Button>
        </div>

        {/* Helper Text */}
        <div style={{ marginTop: '15px', textAlign: 'center' }}>
          <Text type="secondary">
            提示: 您可以询问特定航线的航班，提供日期或其他需求
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default ChatInterface;