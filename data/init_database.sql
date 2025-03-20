
    -- 创建航空公司表
    CREATE TABLE airlines (
        airline_id INT PRIMARY KEY AUTO_INCREMENT,
        airline_name VARCHAR(100) UNIQUE NOT NULL
    );

    -- 创建城市表
    CREATE TABLE cities (
        city_id INT PRIMARY KEY AUTO_INCREMENT,
        city_name VARCHAR(100) UNIQUE NOT NULL
    );

    -- 创建航线表
    CREATE TABLE routes (
        route_id INT PRIMARY KEY AUTO_INCREMENT,
        source_city_id INT,
        destination_city_id INT,
        FOREIGN KEY (source_city_id) REFERENCES cities(city_id),
        FOREIGN KEY (destination_city_id) REFERENCES cities(city_id),
        UNIQUE KEY unique_route (source_city_id, destination_city_id)
    );

    -- 创建航班表
    CREATE TABLE flights (
        flight_id INT PRIMARY KEY AUTO_INCREMENT,
        airline_id INT,
        route_id INT,
        departure_date DATE NOT NULL,
        departure_time TIME NOT NULL,
        duration_minutes INT NOT NULL,
        total_stops INT DEFAULT 0,
        price DECIMAL(10,2) NOT NULL,
        additional_info TEXT,
        FOREIGN KEY (airline_id) REFERENCES airlines(airline_id),
        FOREIGN KEY (route_id) REFERENCES routes(route_id)
    );

    -- 创建预订表
    CREATE TABLE bookings (
        booking_id INT PRIMARY KEY AUTO_INCREMENT,
        flight_id INT,
        user_id INT,
        booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'pending',
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    );
    