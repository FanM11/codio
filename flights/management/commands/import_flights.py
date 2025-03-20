from django.core.management.base import BaseCommand
import pandas as pd
from flights.models import Airline, City, Route, Flight
import os


class Command(BaseCommand):
    help = '从 CSV 文件导入航班数据'

    def handle(self, *args, **kwargs):
        try:
            # 读取 CSV 文件
            csv_path = os.path.join('data', 'processed_flights.csv')
            self.stdout.write(f"正在读取文件: {csv_path}")
            df = pd.read_csv(csv_path)

            # 1. 导入航空公司
            self.stdout.write("导入航空公司...")
            airlines = df['Airline'].unique()
            airline_objects = {}
            for airline_name in airlines:
                airline, created = Airline.objects.get_or_create(name=airline_name)
                airline_objects[airline_name] = airline
            self.stdout.write(self.style.SUCCESS(f"成功导入 {len(airlines)} 个航空公司"))

            # 2. 导入城市
            self.stdout.write("导入城市...")
            cities = set(df['Source'].unique()) | set(df['Destination'].unique())
            city_objects = {}
            for city_name in cities:
                city, created = City.objects.get_or_create(name=city_name)
                city_objects[city_name] = city
            self.stdout.write(self.style.SUCCESS(f"成功导入 {len(cities)} 个城市"))

            # 3. 导入航线
            self.stdout.write("导入航线...")
            routes = df[['Source', 'Destination']].drop_duplicates()
            route_objects = {}
            for _, row in routes.iterrows():
                source = city_objects[row['Source']]
                destination = city_objects[row['Destination']]
                route, created = Route.objects.get_or_create(
                    source_city=source,
                    destination_city=destination
                )
                route_objects[f"{row['Source']}_{row['Destination']}"] = route
            self.stdout.write(self.style.SUCCESS(f"成功导入 {len(routes)} 条航线"))

            # 4. 导入航班
            self.stdout.write("导入航班...")
            flights_created = 0
            for _, row in df.iterrows():
                try:
                    # 解析日期和时间
                    departure_date = pd.to_datetime(row['Date_of_Journey']).date()
                    departure_time = pd.to_datetime(row['Dep_Time']).time()

                    # 获取关联对象
                    airline = airline_objects[row['Airline']]
                    route = route_objects[f"{row['Source']}_{row['Destination']}"]

                    # 创建航班
                    Flight.objects.get_or_create(
                        airline=airline,
                        route=route,
                        departure_date=departure_date,
                        departure_time=departure_time,
                        duration_minutes=row['Duration_Minutes'],
                        total_stops=row['Total_Stops'],
                        price=row['Price'],
                        additional_info=row['Additional_Info']
                    )
                    flights_created += 1

                    if flights_created % 100 == 0:
                        self.stdout.write(f"已导入 {flights_created} 个航班...")

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"导入航班时出错: {str(e)}"))
                    continue

            self.stdout.write(self.style.SUCCESS(f"成功导入 {flights_created} 个航班"))
            self.stdout.write(self.style.SUCCESS("数据导入完成！"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"导入过程中出错: {str(e)}"))