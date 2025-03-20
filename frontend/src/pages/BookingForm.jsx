import React from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';

const BookingForm = () => {
  const navigate = useNavigate();
  const { flightId } = useParams();

 const onFinish = async (values) => {
  try {
    console.log('Submitting booking:', {
      flight: flightId,
      ...values
    });

    const response = await axios.post('http://localhost:8000/api/bookings/', {
      flight: parseInt(flightId), // 确保 flightId 是数字
      user_id: 1,
      passenger_name: values.name,
      passenger_email: values.email,
      passenger_phone: values.phone
    });

    console.log('Booking response:', response.data);
    message.success('预订成功！');

    // 等待一小段时间再跳转
    setTimeout(() => {
      navigate('/bookings');
    }, 1000);
  } catch (error) {
    console.error('Booking error:', error.response?.data || error.message);
    message.error('预订失败：' + (error.response?.data?.detail || error.message));
  }
};
  return (
    <Card title="航班预订" style={{ margin: '24px' }}>
      <Form
        name="booking"
        onFinish={onFinish}
        layout="vertical"
      >
        <Form.Item
          name="name"
          label="乘客姓名"
          rules={[{ required: true, message: '请输入乘客姓名' }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="email"
          label="电子邮箱"
          rules={[
            { required: true, message: '请输入电子邮箱' },
            { type: 'email', message: '请输入有效的电子邮箱' }
          ]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="phone"
          label="联系电话"
          rules={[{ required: true, message: '请输入联系电话' }]}
        >
          <Input />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit">
            确认预订
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default BookingForm;