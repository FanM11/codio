import React, { useState, useEffect } from 'react';
import { Form, DatePicker, Button, Select, Card, List } from 'antd';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const { Option } = Select;

const FlightSearch = () => {
  const navigate = useNavigate();
  const [cities, setCities] = useState([]);
  const [flights, setFlights] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/cities/');
        setCities(response.data);
      } catch (error) {
        console.error('Error fetching cities:', error);
      }
    };

    fetchCities();
  }, []);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/api/flights/search/', {
        source: values.source,
        destination: values.destination,
        date: values.date.format('YYYY-MM-DD')
      });
      setFlights(response.data);
    } catch (error) {
      console.error('Error searching flights:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card title="航班搜索" style={{ marginBottom: '24px' }}>
        <Form
          name="flight_search"
          onFinish={onFinish}
          layout="inline"
          style={{ justifyContent: 'center' }}
        >
          <Form.Item
            name="source"
            rules={[{ required: true, message: '请选择出发城市!' }]}
          >
            <Select
              placeholder="出发城市"
              style={{ width: 200 }}
            >
              {cities.map(city => (
                <Option key={city.id} value={city.name}>{city.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="destination"
            rules={[{ required: true, message: '请选择目的地!' }]}
          >
            <Select
              placeholder="目的地"
              style={{ width: 200 }}
            >
              {cities.map(city => (
                <Option key={city.id} value={city.name}>{city.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="date"
            rules={[{ required: true, message: '请选择日期!' }]}
          >
            <DatePicker style={{ width: 200 }} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              搜索航班
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <List
        itemLayout="horizontal"
        dataSource={flights}
        loading={loading}
        renderItem={flight => (
          <List.Item
            actions={[
              <Button
                type="primary"
                onClick={() => {
                  console.log('Clicking booking button for flight:', flight);
                  navigate(`/booking/${flight.id}`);
                }}
              >
                预订
              </Button>
            ]}
          >
            <List.Item.Meta
              title={`${flight.airline.name} - 航班 ${flight.id}`}
              description={`
                出发: ${flight.departure_time} | 
                时长: ${flight.duration_minutes}分钟 | 
                价格: ￥${flight.price}
              `}
            />
          </List.Item>
        )}
      />
    </div>
  );
};

export default FlightSearch;