import React, { useState } from 'react';
import { Card, Form, Input, Button, Table, Tag, Space, message, Modal, Tabs } from 'antd';
import { SearchOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TabPane } = Tabs;

const BookingManagementPage = () => {
  const [idForm] = Form.useForm();
  const [infoForm] = Form.useForm();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingBooking, setEditingBooking] = useState(null);
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [isCancelModalVisible, setIsCancelModalVisible] = useState(false);
  const [cancelBookingId, setCancelBookingId] = useState(null);

  // 通过ID查询
  const handleIdSearch = async (values) => {
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/bookings/find/?id=${values.bookingId}`);
      setBookings(response.data);
      if (response.data.length === 0) {
        message.info('未找到订单');
      }
    } catch (error) {
      console.error('Error searching bookings:', error);
      message.error('查询失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 通过其他信息查询
  const handleInfoSearch = async (values) => {
    setLoading(true);

    // 构建查询参数
    const params = new URLSearchParams();
    if (values.name) params.append('name', values.name);
    if (values.email) params.append('email', values.email);
    if (values.phone) params.append('phone', values.phone);

    try {
      const response = await axios.get(`http://localhost:8000/api/bookings/find/?${params.toString()}`);
      setBookings(response.data);
      if (response.data.length === 0) {
        message.info('未找到订单');
      }
    } catch (error) {
      console.error('Error searching bookings:', error);
      message.error('查询失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 打开编辑模态框
  const showEditModal = (booking) => {
    setEditingBooking(booking);
    infoForm.setFieldsValue({
      name: booking.passenger_name,
      email: booking.passenger_email,
      phone: booking.passenger_phone
    });
    setIsEditModalVisible(true);
  };

  // 打开取消预订模态框
  const showCancelModal = (bookingId) => {
    setCancelBookingId(bookingId);
    setIsCancelModalVisible(true);
  };

  // 保存编辑修改
  const handleEditSave = async () => {
    try {
      const values = await infoForm.validateFields();
      const response = await axios.patch(`http://localhost:8000/api/bookings/${editingBooking.id}/`, {
        passenger_name: values.name,
        passenger_email: values.email,
        passenger_phone: values.phone
      });

      message.success('订单信息已更新');
      setIsEditModalVisible(false);

      // 更新本地数据
      setBookings(bookings.map(booking =>
        booking.id === editingBooking.id ? response.data : booking
      ));
    } catch (error) {
      console.error('Error updating booking:', error);
      message.error('更新失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 取消预订
  const handleCancelBooking = async () => {
    try {
      const response = await axios.post(`http://localhost:8000/api/bookings/${cancelBookingId}/cancel/`);
      message.success('订单已取消');
      setIsCancelModalVisible(false);

      // 更新本地数据
      setBookings(bookings.map(booking =>
        booking.id === cancelBookingId ? response.data : booking
      ));
    } catch (error) {
      console.error('Error cancelling booking:', error);
      message.error('取消失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '订单号',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '乘客',
      dataIndex: 'passenger_name',
      key: 'passenger_name',
    },
    {
      title: '航班',
      key: 'flight',
      render: (_, record) => (
        <span>
          {record.flight.airline.name} - {record.flight.id}
          <br />
          {record.flight.route.source_city.name} → {record.flight.route.destination_city.name}
        </span>
      ),
    },
    {
      title: '日期/时间',
      key: 'datetime',
      render: (_, record) => (
        <span>
          {record.flight.departure_date}
          <br />
          {record.flight.departure_time}
        </span>
      ),
    },
    {
      title: '联系方式',
      key: 'contact',
      render: (_, record) => (
        <span>
          {record.passenger_email}
          <br />
          {record.passenger_phone}
        </span>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => {
        let color = 'default';
        let text = record.status;

        if (record.status === 'pending') {
          color = 'gold';
          text = '待确认';
        } else if (record.status === 'confirmed') {
          color = 'green';
          text = '已确认';
        } else if (record.status === 'cancelled') {
          color = 'red';
          text = '已取消';
        }

        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
            disabled={record.status === 'cancelled'}
          >
            编辑
          </Button>
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={() => showCancelModal(record.id)}
            disabled={record.status === 'cancelled'}
          >
            取消
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card title="订单管理">
        <Tabs defaultActiveKey="1">
          <TabPane tab="通过订单号查询" key="1">
            <Form
              form={idForm}
              layout="inline"
              onFinish={handleIdSearch}
              style={{ marginBottom: '20px' }}
            >
              <Form.Item
                name="bookingId"
                rules={[{ required: true, message: '请输入订单号' }]}
              >
                <Input placeholder="订单号" prefix={<SearchOutlined />} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>
                  查询
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          <TabPane tab="通过个人信息查询" key="2">
            <Form
              form={infoForm}
              layout="inline"
              onFinish={handleInfoSearch}
              style={{ marginBottom: '20px' }}
            >
              <Form.Item name="name">
                <Input placeholder="乘客姓名" />
              </Form.Item>
              <Form.Item name="email">
                <Input placeholder="电子邮箱" />
              </Form.Item>
              <Form.Item name="phone">
                <Input placeholder="手机号码" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>
                  查询
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>

        <Table
          columns={columns}
          dataSource={bookings}
          rowKey="id"
          loading={loading}
          pagination={false}
          bordered
          style={{ marginTop: '20px' }}
        />
      </Card>

      {/* 编辑订单模态框 */}
      <Modal
        title="编辑订单信息"
        visible={isEditModalVisible}
        onOk={handleEditSave}
        onCancel={() => setIsEditModalVisible(false)}
      >
        <Form
          form={infoForm}
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
        </Form>
      </Modal>

      {/* 取消订单确认模态框 */}
      <Modal
        title="确认取消预订"
        visible={isCancelModalVisible}
        onOk={handleCancelBooking}
        onCancel={() => setIsCancelModalVisible(false)}
        okText="确认取消"
        cancelText="返回"
        okButtonProps={{ danger: true }}
      >
        <p>您确定要取消该预订吗？此操作无法撤销。</p>
      </Modal>
    </div>
  );
};

export default BookingManagementPage;