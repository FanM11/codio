import pandas as pd
import numpy as np
from datetime import datetime
import os

# 设置项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')


def preprocess_flights_data():
    """
    预处理航班数据
    """
    try:
        # 设置输入输出文件路径
        input_file = os.path.join(DATA_DIR, 'flights.csv')
        output_file = os.path.join(DATA_DIR, 'processed_flights.csv')

        print(f"开始处理数据文件: {input_file}")

        # 读取数据
        df = pd.read_csv(input_file)
        print(f"成功读取数据，共 {len(df)} 条记录")

        # 1. 处理日期时间
        print("正在处理日期和时间...")

        def parse_duration(duration_str):
            try:
                hours = 0
                minutes = 0
                if pd.isna(duration_str):  # 处理空值
                    return 0
                if 'h' in str(duration_str):
                    hours = int(str(duration_str).split('h')[0])
                    if 'm' in str(duration_str):
                        minutes = int(str(duration_str).split('h')[1].replace('m', ''))
                elif 'm' in str(duration_str):
                    minutes = int(str(duration_str).replace('m', ''))
                return hours * 60 + minutes
            except:
                return 0

        # 转换日期格式
        df['Date_of_Journey'] = pd.to_datetime(df['Date_of_Journey'])

        # 转换出发时间为标准格式
        df['Dep_Time'] = pd.to_datetime(df['Dep_Time'], format='%H:%M').dt.time

        # 转换航班持续时间为分钟
        df['Duration_Minutes'] = df['Duration'].apply(parse_duration)

        # 2. 处理航班停靠
        print("正在处理航班停靠信息...")
        df['Total_Stops'] = df['Total_Stops'].fillna('0 stop')
        df['Total_Stops'] = df['Total_Stops'].str.extract('(\d+)').fillna(0).astype(int)

        # 3. 处理航空公司信息
        print("正在处理航空公司信息...")
        df['Airline'] = df['Airline'].fillna('Unknown')

        # 4. 处理城市信息
        print("正在处理城市信息...")
        df['Source'] = df['Source'].fillna('Unknown')
        df['Destination'] = df['Destination'].fillna('Unknown')

        # 5. 价格处理
        print("正在处理价格信息...")
        df['Price'] = df['Price'].fillna(df['Price'].mean())
        df['Price_Normalized'] = (df['Price'] - df['Price'].mean()) / df['Price'].std()

        # 6. 创建新的特征
        print("正在创建新特征...")

        def get_hour(time_obj):
            if pd.isna(time_obj):
                return 0
            return time_obj.hour

        df['Is_Morning_Flight'] = df['Dep_Time'].apply(
            lambda x: True if get_hour(x) >= 5 and get_hour(x) < 12 else False
        )

        df['Additional_Info'] = df['Additional_Info'].fillna('No Info')
        df['Is_International'] = df['Additional_Info'].str.contains(
            'International', case=False, na=False
        )

        # 7. 添加航线ID（使用字符串而不是分类数据）
        print("正在创建航线ID...")
        df['Route_ID'] = df['Source'].astype(str) + '_' + df['Destination'].astype(str)

        # 8. 将特定列转换为分类类型（在所有字符串操作之后）
        df['Airline'] = df['Airline'].astype('category')
        df['Source'] = df['Source'].astype('category')
        df['Destination'] = df['Destination'].astype('category')

        # 保存处理后的数据
        print(f"正在保存处理后的数据到: {output_file}")
        df.to_csv(output_file, index=False)

        # 生成统计信息
        stats = {
            'total_flights': len(df),
            'unique_airlines': df['Airline'].nunique(),
            'unique_routes': df['Route_ID'].nunique(),
            'avg_price': round(df['Price'].mean(), 2),
            'avg_duration': round(df['Duration_Minutes'].mean(), 2),
            'unique_sources': df['Source'].nunique(),
            'unique_destinations': df['Destination'].nunique()
        }

        # 保存统计信息
        stats_file = os.path.join(DATA_DIR, 'data_stats.txt')
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("数据统计信息:\n")
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")

        print("数据处理完成！")
        print("\n基本统计信息:")
        for key, value in stats.items():
            print(f"{key}: {value}")

        return True, stats

    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        return False, str(e)


def generate_database_script():
    """
    生成数据库初始化脚本
    """
    print("正在生成数据库初始化脚本...")
    sql_script = """
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
    """

    # 保存SQL脚本
    sql_file = os.path.join(DATA_DIR, 'init_database.sql')
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(sql_script)
    print(f"数据库初始化脚本已保存到: {sql_file}")


if __name__ == "__main__":
    print("开始数据预处理流程...")
    success, result = preprocess_flights_data()

    if success:
        # 生成数据库脚本
        generate_database_script()
        print("\n全部处理完成！")
    else:
        print(f"\n处理失败: {result}")