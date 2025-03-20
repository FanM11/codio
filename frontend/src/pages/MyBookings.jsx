import React, { useState, useEffect } from 'react';
import { List, Card, Tag, Button, message } from 'antd';
import axios from 'axios';

const MyBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchBookings = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('开始获取预订列表...');
      const response = await axios.get('http://localhost:8000/api/bookings/');
      console.log('获取到的预订数据:', response.data);

      if (Array.isArray(response.data)) {
        setBookings(response.data);
      } else {
        console.error('返回的数据不是数组:', response.data);
        setError('数据格式错误');
      }
    } catch (error) {
      console.error('获取预订列表失败:', error);
      setError(error.message);
      message.error('获取订单失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时获取数据
  // 添加到现有的 MyBookings.jsx 组件中
  useEffect(() => {
    // 首次加载数据
    fetchBookings();

    // 每5秒刷新一次
    // const interval = setInterval(fetchBookings, 5000);

    // 组件卸载时清除定时器
    // return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="我的订单"
        extra={
          <Button onClick={fetchBookings} type="link">
            刷新
          </Button>
        }
      >
        {error && (
          <div style={{ color: 'red', marginBottom: '16px' }}>
            错误: {error}
          </div>
        )}

        {loading ? (
          <div>加载中...</div>
        ) : bookings.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px' }}>
            暂无订单
          </div>
        ) : (
          <List
            dataSource={bookings}
            renderItem={booking => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>预订号: {booking.id}</span>
                      <Tag color={
                        booking.status === 'pending' ? 'gold' :
                        booking.status === 'confirmed' ? 'green' : 'red'
                      }>
                        {booking.status === 'pending' ? '待确认' :
                         booking.status === 'confirmed' ? '已确认' : '已取消'}
                      </Tag>
                    </div>
                  }
                  description={
                    <>
                      <p>航班: {booking.flight?.airline?.name}
                         - {booking.flight?.route?.source_city?.name}
                         到 {booking.flight?.route?.destination_city?.name}</p>
                      <p>乘客: {booking.passenger_name}</p>
                      <p>联系方式: {booking.passenger_email} | {booking.passenger_phone}</p>
                    </>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
};

export default MyBookings;