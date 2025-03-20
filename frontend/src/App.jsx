import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  HomeOutlined,
  SearchOutlined,
  FileTextOutlined,
  MessageOutlined,
  SettingOutlined
} from '@ant-design/icons';

import FlightSearch from './pages/FlightSearch';
import MyBookings from './pages/MyBookings';
import BookingForm from './pages/BookingForm';
import ChatInterface from './pages/ChatInterface';
import BookingManagementPage from './pages/BookingManagementPage';

const { Header, Content, Footer } = Layout;

function App() {
  return (
    <Router>
      <Layout className="layout" style={{ minHeight: '100vh' }}>
        <Header>
          <div className="logo" />
          <Menu theme="dark" mode="horizontal" defaultSelectedKeys={['1']}>
            <Menu.Item key="1" icon={<SearchOutlined />}>
              <Link to="/">航班搜索</Link>
            </Menu.Item>
            <Menu.Item key="2" icon={<FileTextOutlined />}>
              <Link to="/bookings">我的订单</Link>
            </Menu.Item>
            <Menu.Item key="3" icon={<MessageOutlined />}>
              <Link to="/chat">智能助手</Link>
            </Menu.Item>
            <Menu.Item key="4" icon={<SettingOutlined />}>
              <Link to="/manage">订单管理</Link>
            </Menu.Item>
          </Menu>
        </Header>
        <Content style={{ padding: '0 50px' }}>
          <div className="site-layout-content">
            <Routes>
              <Route path="/" element={<FlightSearch />} />
              <Route path="/bookings" element={<MyBookings />} />
              <Route path="/booking/:flightId" element={<BookingForm />} />
              <Route path="/chat" element={<ChatInterface />} />
              <Route path="/manage" element={<BookingManagementPage />} />
            </Routes>
          </div>
        </Content>
        <Footer style={{ textAlign: 'center' }}>Flight Booking System ©2025</Footer>
      </Layout>
    </Router>
  );
}

export default App;