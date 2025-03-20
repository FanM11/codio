import logging
import re
import json
from datetime import datetime
from openai import OpenAI
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ChatSystem')


class ChatGLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key="175535b2d5ea490e8692274038855dce.wTalpOrFZ5WIgCaL",
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )

    def get_response(self, message, context=None):
        try:
            # System prompt
            system_prompt = (
                "You are a professional flight booking assistant. Please follow these rules:\n"
                "1. Remember all user-provided information\n"
                "2. Don't ask for information already provided\n"
                "3. Only ask for essential missing information\n"
                "4. Be concise and professional\n"
                "5. Required information: departure city, destination city, date\n"
                "6. Optional information: preferred time, contact details"
            )

            messages = [{"role": "system", "content": system_prompt}]

            # Add context if available
            if context and any(value for value in context.values() if value is not None):
                context_info = []
                if context.get('source_city'):
                    context_info.append(f"Departure: {context['source_city']}")
                if context.get('destination_city'):
                    context_info.append(f"Destination: {context['destination_city']}")
                if context.get('date'):
                    context_info.append(f"Date: {context['date']}")
                if context.get('selected_flight'):
                    context_info.append(f"Selected Flight: {context['selected_flight']}")
                if context.get('booking_stage'):
                    context_info.append(f"Booking Stage: {context['booking_stage']}")
                if context.get('preferred_time'):
                    context_info.append(f"Preferred Time: {context['preferred_time']}")

                if context_info:
                    context_str = "Known information: " + "; ".join(context_info)
                    messages.append({"role": "assistant", "content": context_str})

            # Add user message
            messages.append({"role": "user", "content": message})

            logger.info(f"Sending request with messages: {messages}")

            # Call API
            response = self.client.chat.completions.create(
                model="glm-4",
                messages=messages,
                temperature=0.3,
                top_p=0.95,
            )

            response_text = response.choices[0].message.content.strip()
            logger.info(f"Raw response: {response_text}")

            return {
                "response": response_text,
                "extracted_info": {}
            }

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            return {
                "response": "Sorry, there was a system error. Please try again.",
                "extracted_info": {}
            }

    def extract_structured_info(self, message, current_context):
        """使用LLM提取结构化信息"""
        try:
            # 简化提示，避免格式问题
            prompt = f"""
            Extract flight booking information from this message: "{message}"

            Current known information:
            - Departure: {current_context.get('source_city', 'Unknown')}
            - Destination: {current_context.get('destination_city', 'Unknown')}
            - Date: {current_context.get('departure_date', 'Unknown')}

            Return ONLY a valid JSON with the following structure (include only fields with information):
            {{
                "source_city": extracted departure city or null,
                "destination_city": extracted destination city or null,
                "departure_date": extracted date in YYYY-MM-DD format or null,
                "passenger_name": extracted name or null,
                "passenger_email": extracted email WITHOUT any prefix or null,
                "passenger_phone": extracted phone or null,
                "selected_flight_option": extracted flight number or null,
                "preferred_time": extracted time preference (morning/afternoon/evening) or null,
                "modification_intent": true/false,
                "reset_flight_selection": true/false,
                "confirm_booking": true/false
            }}
            """

            response = self.client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": "You extract structured information from text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            response_text = response.choices[0].message.content.strip()

            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON: {json_str}")
                    return {}
            else:
                logger.error(f"No JSON found in response: {response_text}")
                return {}

            # 清理邮箱格式
            if result.get('passenger_email'):
                email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', result['passenger_email'])
                if email_match:
                    result['passenger_email'] = email_match.group(1)

            return result
        except Exception as e:
            logger.error(f"LLM extraction error: {str(e)}")
            return {}


class DialogManager:
    def __init__(self):
        self.llm_client = ChatGLMClient()
        self.session_id = None

    def extract_email(self, message):
        """提取邮箱地址，并处理各种前缀"""
        # 首先尝试带前缀的完整模式
        prefix_patterns = [
            r'(?:邮箱|email|邮件|电子邮件|电邮)[是为:：\s]*?([\w\.-]+@[\w\.-]+\.\w+)',
            r'(?:邮箱|email|邮件|电子邮件|电邮)[是为]?\s*([\w\.-]+@[\w\.-]+\.\w+)',
        ]

        for pattern in prefix_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # 然后尝试直接匹配邮箱格式
        direct_match = re.search(r'\b([\w\.-]+@[\w\.-]+\.\w+)\b', message)
        if direct_match:
            return direct_match.group(1).strip()

        return None

    def _extract_info_from_message(self, message):
        """使用正则表达式从消息中提取信息"""
        info = {}

        # 处理重选航班的请求
        if '重新选择' in message or '重选' in message or '换航班' in message or '其他航班' in message:
            info['reset_flight_selection'] = True
            logger.info("User requested to select a different flight")
            return info

        # Extract cities using different patterns
        city_patterns = [
            r'from\s*([\w\s]+)\s*to\s*([\w\s]+)',  # English pattern
            r'从\s*([\w\s]+)\s*到\s*([\w\s]+)',  # Chinese pattern
        ]

        for pattern in city_patterns:
            city_match = re.search(pattern, message, re.IGNORECASE)
            if city_match:
                source = self._standardize_city_name(city_match.group(1).strip())
                dest = self._standardize_city_name(city_match.group(2).strip())
                if source and dest:
                    info['source_city'] = source
                    info['destination_city'] = dest
                    logger.info(f"Found cities: {source} -> {dest}")
                    break

        # Extract date (support both formats)
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}\.\d{1,2}\.\d{1,2}',
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, message)
            if date_match:
                date_str = date_match.group().replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-')
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    info['departure_date'] = date.date()
                    logger.info(f"Found date: {date.date()}")
                    break
                except ValueError:
                    logger.error(f"Invalid date format: {date_str}")

        # Extract flight number selection
        flight_number_pattern = r'\b(?:选择|选|flight|航班|选项|option)\s*(?:号码|号|number|#)?\s*[:#]?\s*(\d+)\b'
        flight_match = re.search(flight_number_pattern, message, re.IGNORECASE)
        if flight_match:
            try:
                selected_option = int(flight_match.group(1))
                info['selected_flight_option'] = selected_option
                logger.info(f"Found selected flight option: {selected_option}")
            except ValueError:
                logger.error(f"Invalid flight option number")

        # Try direct number input (1-5)
        elif re.match(r'^\s*[1-5]\s*$', message):
            info['selected_flight_option'] = int(message.strip())
            logger.info(f"Found direct flight option number: {info['selected_flight_option']}")

        # 更精确的姓名提取
        name_pattern = r'(?:我叫|my name is|name[:\s]+|姓名[:\s]+|我的名字是|名字[是为:：\s]+)[\s:：]*([^\n,\.。，;；]+)'
        name_match = re.search(name_pattern, message, re.IGNORECASE)
        if name_match:
            info['passenger_name'] = name_match.group(1).strip()
            logger.info(f"Found passenger name: {info['passenger_name']}")

        # 更精确的电话提取
        phone_pattern = r'(?:电话|phone|tel|联系方式|手机|联系电话|号码)[是为:：\s]*([0-9+\-\s]{8,})'
        phone_match = re.search(phone_pattern, message, re.IGNORECASE)
        if phone_match:
            info['passenger_phone'] = re.sub(r'\s+', '', phone_match.group(1).strip())  # 移除所有空格
            logger.info(f"Found phone: {info['passenger_phone']}")
        # 直接手机号格式
        elif re.search(r'\b\d{11}\b', message):  # 中国手机号
            info['passenger_phone'] = re.search(r'\b\d{11}\b', message).group(0)
            logger.info(f"Found phone (direct): {info['passenger_phone']}")

        # 提取邮箱地址
        email = self.extract_email(message)
        if email:
            info['passenger_email'] = email
            logger.info(f"Found email: {info['passenger_email']}")

        # 提取时间偏好
        if '上午' in message or '早' in message or 'morning' in message.lower():
            info['preferred_time'] = 'morning'
            logger.info(f"Found time preference: morning")
        elif '下午' in message or 'afternoon' in message.lower():
            info['preferred_time'] = 'afternoon'
            logger.info(f"Found time preference: afternoon")
        elif '晚上' in message or '夜' in message or 'evening' in message.lower() or 'night' in message.lower():
            info['preferred_time'] = 'evening'
            logger.info(f"Found time preference: evening")

        # 检查确认意图
        if '确认' in message or 'confirm' in message.lower() or '是的' in message or 'yes' in message.lower():
            info['confirm_booking'] = True
            logger.info("User confirmed booking")

        # 检查修改意图
        if '修改' in message or 'modify' in message.lower() or 'change' in message.lower() or 'edit' in message.lower():
            info['modification_intent'] = True
            logger.info("User requested to modify booking")

        logger.info(f"Extracted info using regex: {info}")
        return info

    def _extract_info_with_llm(self, message, current_context):
        """使用LLM提取信息，能够理解更复杂的上下文和模糊表达"""
        extracted_info = self.llm_client.extract_structured_info(message, current_context)
        logger.info(f"Extracted info using LLM: {extracted_info}")
        return extracted_info

    def _standardize_city_name(self, city_name):
        """Standardize city name to match database"""
        try:
            from .models import City
            city = City.objects.filter(name__iexact=city_name).first()
            logger.info(f"Standardized city name: {city_name} -> {city.name if city else None}")
            return city.name if city else None
        except Exception as e:
            logger.error(f"Error standardizing city name: {e}")
            return None

    def _get_session_info(self):
        """Get current session information"""
        try:
            from .models import TempBooking
            booking = TempBooking.objects.get(
                session_id=self.session_id,
                status='pending'
            )
            logger.info(f"Retrieved booking for session {self.session_id}: {booking}")

            if booking:
                logger.info(
                    f"Found booking with cities: {booking.source_city} -> {booking.destination_city}, date: {booking.departure_date}")
            return booking
        except TempBooking.DoesNotExist:
            # 如果不存在则创建新的
            booking = TempBooking.objects.create(
                session_id=self.session_id,
                status='pending'
            )
            logger.info(f"Created new booking for session {self.session_id}")
            return booking
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None

    def _save_to_temp_booking(self, info):
        """Save information to temporary booking"""
        try:
            from .models import TempBooking, City, Flight
            logger.info(f"Saving info to session {self.session_id}: {info}")

            # 获取现有预订
            booking = self._get_session_info()
            if not booking:
                return False

            # 在存储邮箱前清理
            if info.get('passenger_email') and '@' in info['passenger_email']:
                email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', info['passenger_email'])
                if email_match:
                    info['passenger_email'] = email_match.group(1)
                    logger.info(f"Cleaned email to: {info['passenger_email']}")

            # 只更新提供的信息，保留现有信息
            if info.get('source_city'):
                source_city = City.objects.filter(name__iexact=info['source_city']).first()
                if source_city:
                    booking.source_city = source_city
                    logger.info(f"Updated source city to: {source_city.name}")

            if info.get('destination_city'):
                dest_city = City.objects.filter(name__iexact=info['destination_city']).first()
                if dest_city:
                    booking.destination_city = dest_city
                    logger.info(f"Updated destination city to: {dest_city.name}")

            if info.get('departure_date'):
                booking.departure_date = info['departure_date']
                logger.info(f"Updated departure date to: {info['departure_date']}")

            if info.get('preferred_time'):
                booking.preferred_time = info['preferred_time']
                logger.info(f"Updated preferred time to: {info['preferred_time']}")

            # 处理选择的航班
            if info.get('selected_flight_option') and booking.available_flights:
                try:
                    # 获取之前保存的可用航班ID列表
                    available_flight_ids = booking.available_flights.split(',')
                    selected_index = info['selected_flight_option'] - 1  # 转为0-based索引

                    # 验证选择的索引是否有效
                    if 0 <= selected_index < len(available_flight_ids):
                        selected_flight_id = int(available_flight_ids[selected_index])
                        booking.selected_flight_id = selected_flight_id
                        booking.booking_stage = 'collecting_info'
                        logger.info(
                            f"Selected flight ID: {selected_flight_id}, updated booking stage to collecting_info")
                    else:
                        logger.error(
                            f"Invalid flight selection index: {selected_index}, available options: {len(available_flight_ids)}")
                except Exception as e:
                    logger.error(f"Error processing flight selection: {e}")

            # 处理乘客信息
            if info.get('passenger_name'):
                booking.passenger_name = info['passenger_name']
                logger.info(f"Updated passenger name to: {info['passenger_name']}")

            if info.get('passenger_email'):
                booking.passenger_email = info['passenger_email']
                logger.info(f"Updated passenger email to: {info['passenger_email']}")

            if info.get('passenger_phone'):
                booking.passenger_phone = info['passenger_phone']
                logger.info(f"Updated passenger phone to: {info['passenger_phone']}")

            # 检查是否所有乘客信息都已提供，如果已提供则更新阶段为确认阶段
            if booking.passenger_name and booking.passenger_email and booking.passenger_phone and booking.selected_flight_id:
                booking.booking_stage = 'confirming'
                logger.info("All passenger info collected, updated booking stage to confirming")

            booking.save()
            logger.info(f"Successfully saved booking: {booking.id}")
            return True

        except Exception as e:
            logger.error(f"Error saving temp booking: {e}")
            return False

    def _create_final_booking(self, temp_booking):
        """Create final booking from temporary booking"""
        try:
            from .models import Booking, Flight

            # 验证所需信息是否齐全
            if not temp_booking.selected_flight_id or not temp_booking.passenger_name or \
                    not temp_booking.passenger_email or not temp_booking.passenger_phone:
                logger.error("Missing required information for final booking")
                logger.error(f"Flight: {temp_booking.selected_flight_id}, Name: {temp_booking.passenger_name}, "
                             f"Email: {temp_booking.passenger_email}, Phone: {temp_booking.passenger_phone}")
                return None

            # 获取选定的航班
            try:
                flight = Flight.objects.get(id=temp_booking.selected_flight_id)
            except Flight.DoesNotExist:
                logger.error(f"Selected flight not found: {temp_booking.selected_flight_id}")
                return None

            # 清理邮箱中的可能前缀
            clean_email = temp_booking.passenger_email
            if '@' in clean_email:
                # 如果邮箱中包含前缀描述，只保留实际邮箱部分
                email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', clean_email)
                if email_match:
                    clean_email = email_match.group(1)
                    logger.info(f"Cleaned email from '{temp_booking.passenger_email}' to '{clean_email}'")

            # 创建正式预订
            booking = Booking.objects.create(
                flight=flight,
                user_id=1,  # 默认用户ID，实际应用中可能需要真实用户
                passenger_name=temp_booking.passenger_name,
                passenger_email=clean_email,  # 使用清理后的邮箱
                passenger_phone=temp_booking.passenger_phone,
                status='confirmed'
            )

            # 更新临时预订状态
            temp_booking.status = 'confirmed'
            temp_booking.save()

            logger.info(f"Created final booking: {booking.id}")
            return booking

        except Exception as e:
            logger.error(f"Error creating final booking: {e}")
            return None

    def _handle_modification_request(self, booking):
        """处理用户要求修改预订信息的请求"""
        try:
            # 将状态设置回信息收集阶段
            booking.booking_stage = 'collecting_info'
            booking.save()

            # 构建已有信息摘要和修改指南
            response = "请告诉我您想修改的信息。目前的预订信息如下：\n\n"

            # 添加航班信息
            flight_info = "航班信息未找到"
            try:
                from .models import Flight
                flight = Flight.objects.get(id=booking.selected_flight_id)

                # 确定时间段
                time_period = ""
                hour = flight.departure_time.hour
                if 5 <= hour < 12:
                    time_period = "【上午】"
                elif 12 <= hour < 18:
                    time_period = "【下午】"
                else:
                    time_period = "【晚上】"

                flight_info = (
                    f"航班: {flight.airline.name} - {flight.id}\n"
                    f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                    f"日期: {flight.departure_date}\n"
                    f"时间: {time_period}{flight.departure_time}\n"
                    f"价格: ¥{flight.price}"
                )
            except Exception as e:
                logger.error(f"Error getting flight info for modification: {e}")

            response += flight_info + "\n\n"

            # 清理和显示邮箱
            clean_email = booking.passenger_email
            if clean_email and '@' in clean_email:
                email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', clean_email)
                if email_match:
                    clean_email = email_match.group(1)

            # 添加乘客信息
            passenger_info = (
                f"乘客: {booking.passenger_name or '未提供'}\n"
                f"电子邮件: {clean_email or '未提供'}\n"
                f"电话: {booking.passenger_phone or '未提供'}"
            )

            response += passenger_info + "\n\n"

            # 添加修改指南
            response += (
                "您可以通过以下方式修改信息：\n"
                "- 修改姓名: 例如「我的名字是张三」\n"
                "- 修改邮箱: 例如「我的邮箱是example@email.com」\n"
                "- 修改电话: 例如「我的电话是13800138000」\n\n"
                "如果要选择其他航班，请回复「重新选择航班」。\n"
                "完成修改后，请回复「确认」完成预订。"
            )

            return response

        except Exception as e:
            logger.error(f"Error handling modification request: {e}")
            return "抱歉，处理修改请求时出错。请重试。"

    def _collect_passenger_info(self, booking):
        """收集乘客信息"""
        try:
            from .models import Flight

            flight = Flight.objects.get(id=booking.selected_flight_id)

            # 确定时间段
            time_period = ""
            hour = flight.departure_time.hour
            if 5 <= hour < 12:
                time_period = "【上午】"
            elif 12 <= hour < 18:
                time_period = "【下午】"
            else:
                time_period = "【晚上】"

            # 创建标准的信息收集提示
            missing_info = []
            if not booking.passenger_name:
                missing_info.append("姓名")

            # 检查邮箱 - 如果有前缀问题，也视为缺失
            has_valid_email = False
            if booking.passenger_email:
                email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', booking.passenger_email)
                if email_match:
                    has_valid_email = True

            if not has_valid_email:
                missing_info.append("电子邮件")

            if not booking.passenger_phone:
                missing_info.append("联系电话")

            if not missing_info:
                # 所有信息都已收集，进入确认阶段
                booking.booking_stage = 'confirming'
                booking.save()

                # 清理邮箱显示
                clean_email = booking.passenger_email
                if '@' in clean_email:
                    email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', clean_email)
                    if email_match:
                        clean_email = email_match.group(1)

                return (
                    f"请确认您的订单信息:\n\n"
                    f"航班信息\n"
                    f"航班: {flight.airline.name} - {flight.id}\n"
                    f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                    f"日期: {flight.departure_date}\n"
                    f"时间: {time_period}{flight.departure_time}\n"
                    f"价格: ¥{flight.price}\n\n"
                    f"乘客信息\n"
                    f"乘客: {booking.passenger_name}\n"
                    f"电子邮件: {clean_email}\n"
                    f"电话: {booking.passenger_phone}\n\n"
                    f"请回复\"确认\"完成预订，或回复\"修改\"更改信息。"
                )

            # 构建已选航班的信息
            response = (
                f"您已选择以下航班:\n"
                f"航班号: {flight.id}\n"
                f"航空公司: {flight.airline.name}\n"
                f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                f"日期: {flight.departure_date}\n"
                f"时间: {time_period}{flight.departure_time}\n"
                f"价格: ¥{flight.price}\n\n"
            )

            # 添加需要收集的信息提示和已有信息提示
            if missing_info:
                response += f"请提供以下乘客信息以完成预订: {', '.join(missing_info)}"

            # 提供已有信息的反馈
            if booking.passenger_name:
                response += f"\n已提供的姓名: {booking.passenger_name}"

            if booking.passenger_phone:
                response += f"\n已提供的电话: {booking.passenger_phone}"

            if booking.passenger_email and has_valid_email:
                # 显示干净的邮箱
                email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', booking.passenger_email)
                if email_match:
                    response += f"\n已提供的邮箱: {email_match.group(1)}"
                else:
                    response += f"\n已提供的邮箱: {booking.passenger_email}"

            return response

        except Exception as e:
            logger.error(f"Error collecting passenger info: {e}")
            return "抱歉，处理乘客信息时出错。请重试。"

    def _search_flights(self, booking):
        """Search for available flights and handle booking process"""
        try:
            from .models import Flight

            # 获取符合条件的航班
            flights = Flight.objects.filter(
                route__source_city=booking.source_city,
                route__destination_city=booking.destination_city,
                departure_date=booking.departure_date
            ).select_related('airline', 'route')

            if not flights.exists():
                return f"抱歉，没有找到从 {booking.source_city.name} 到 {booking.destination_city.name} 在 {booking.departure_date} 的航班。"

            # 更新预订状态为选择航班阶段
            booking.booking_stage = 'selecting'
            booking.save()

            # 处理时间偏好
            preferred_time = booking.preferred_time
            morning_flights = []
            afternoon_flights = []
            evening_flights = []

            # 将航班按时间段分类
            for flight in flights:
                hour = flight.departure_time.hour
                if 5 <= hour < 12:
                    morning_flights.append(flight)
                elif 12 <= hour < 18:
                    afternoon_flights.append(flight)
                else:
                    evening_flights.append(flight)

            # 根据偏好排序航班
            sorted_flights = []
            message_prefix = ""

            if preferred_time == 'morning' or (preferred_time and ('上午' in preferred_time or '早' in preferred_time)):
                sorted_flights = morning_flights + afternoon_flights + evening_flights
                message_prefix = "根据您的上午时间偏好，为您优先推荐上午航班:\n\n"
            elif preferred_time == 'afternoon' or (preferred_time and '下午' in preferred_time):
                sorted_flights = afternoon_flights + morning_flights + evening_flights
                message_prefix = "根据您的下午时间偏好，为您优先推荐下午航班:\n\n"
            elif preferred_time == 'evening' or (preferred_time and ('晚上' in preferred_time or '夜' in preferred_time)):
                sorted_flights = evening_flights + afternoon_flights + morning_flights
                message_prefix = "根据您的晚上时间偏好，为您优先推荐晚上航班:\n\n"
            else:
                sorted_flights = list(flights)
                message_prefix = "为您找到以下航班:\n\n"

            # 构建航班信息响应
            response = message_prefix

            # 显示前5个航班
            displayed_flights = sorted_flights[:5]
            for i, flight in enumerate(displayed_flights, 1):
                # 添加时间段标记
                time_period = ""
                hour = flight.departure_time.hour
                if 5 <= hour < 12:
                    time_period = "【上午】"
                elif 12 <= hour < 18:
                    time_period = "【下午】"
                else:
                    time_period = "【晚上】"

                response += (
                    f"航班选项 {i}:\n"
                    f"航班号: {flight.id}\n"
                    f"航空公司: {flight.airline.name}\n"
                    f"出发时间: {time_period}{flight.departure_time}\n"
                    f"飞行时长: {flight.duration_minutes} 分钟\n"
                    f"价格: ¥{flight.price}\n\n"
                )

            response += "请选择航班号进行预订。选择后我会为您收集联系信息。"

            # 将航班选项保存到临时预订中
            booking.available_flights = ','.join(str(f.id) for f in displayed_flights)
            booking.save()

            return response

        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            return "抱歉，搜索航班时发生错误。请重试。"

    def process_message(self, message):
        try:
            if not self.session_id:
                return "Session error. Please refresh the page."

            # 获取当前预订信息
            current_booking = self._get_session_info()
            logger.info(f"Current booking info: {current_booking}")

            # 检查是否处于修改订单状态
            if current_booking.booking_stage == 'modifying' and current_booking.modification_id:
                return self._handle_booking_modification(message, current_booking)

            # 检查是否是订单查询、修改或取消请求
            if ('订单' in message or '预订' in message or '查询' in message or '取消' in message or
                    'booking' in message.lower() or 'order' in message.lower() or 'cancel' in message.lower() or
                    'reservation' in message.lower() or re.search(r'#\d+', message)):
                # 尝试提取订单查询参数
                booking_params = self._extract_booking_query_params(message)
                if booking_params:
                    return self._handle_booking_query(message)

            # 尝试使用LLM进行全面理解
            try:
                # 尝试解析整个消息，看是否包含完整预订信息
                whole_message_analysis = self.llm_client.extract_structured_info(message, {
                    'source_city': None,
                    'destination_city': None,
                    'departure_date': None
                })

                # 如果有城市和日期信息，可能是一次性提供了所有信息
                if whole_message_analysis.get('source_city') and whole_message_analysis.get(
                        'destination_city') and whole_message_analysis.get('departure_date'):
                    logger.info(f"Detected complete booking info in a single message: {whole_message_analysis}")
                    # 这里可以优化流程，直接跳到下一步
            except Exception as e:
                logger.error(f"Error in whole message analysis: {e}")
                # 失败了继续正常流程，不影响核心功能

            # 准备当前上下文信息用于LLM提取
            current_context = {
                'source_city': current_booking.source_city.name if current_booking.source_city else None,
                'destination_city': current_booking.destination_city.name if current_booking.destination_city else None,
                'departure_date': current_booking.departure_date.strftime(
                    '%Y-%m-%d') if current_booking.departure_date else None,
                'passenger_name': current_booking.passenger_name,
                'passenger_email': current_booking.passenger_email,
                'passenger_phone': current_booking.passenger_phone,
                'selected_flight_id': current_booking.selected_flight_id,
                'booking_stage': current_booking.booking_stage,
                'preferred_time': current_booking.preferred_time
            }

            # 1. 使用正则表达式提取信息
            regex_info = self._extract_info_from_message(message)

            # 2. 使用LLM提取信息 - 能够理解更复杂的表达
            llm_info = self._extract_info_with_llm(message, current_context)

            # 3. 合并信息，优先使用正则表达式提取的结果
            new_info = {}
            # 先添加正则表达式的结果
            for key, value in regex_info.items():
                if value is not None:
                    new_info[key] = value

            # 再添加LLM的结果，但只添加正则表达式没有提取到的字段
            for key, value in llm_info.items():
                if key not in new_info or new_info[key] is None:
                    if value is not None:
                        new_info[key] = value

            logger.info(f"Combined extracted info: {new_info}")

            # 处理修改请求
            if (new_info.get('modification_intent') or
                    (current_booking.booking_stage == 'confirming' and (
                            '修改' in message or 'modify' in message.lower() or 'change' in message.lower() or 'edit' in message.lower()))):
                return self._handle_modification_request(current_booking)

            # 处理重选航班的请求
            if new_info.get('reset_flight_selection'):
                # 重置航班选择
                current_booking.selected_flight_id = None
                current_booking.booking_stage = 'searching'  # 或者 'selecting'，取决于您希望从哪步开始
                current_booking.save()

                # 重新搜索航班
                return self._search_flights(current_booking)

            # 处理确认预订
            if (new_info.get('confirm_booking') or
                    (current_booking.booking_stage == 'confirming' and (
                            '确认' in message or 'confirm' in message.lower() or '是的' in message or 'yes' in message.lower()))):
                # 通过提取的邮箱清理函数处理邮箱
                if current_booking.passenger_email and '@' in current_booking.passenger_email:
                    email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', current_booking.passenger_email)
                    if email_match:
                        current_booking.passenger_email = email_match.group(1)
                        current_booking.save()

                booking = self._create_final_booking(current_booking)
                if booking:
                    return f"预预订成功! 您的订单编号是: {booking.id}。您已成功预订从 {booking.flight.route.source_city.name} 到 {booking.flight.route.destination_city.name} 的航班，起飞时间: {booking.flight.departure_date} {booking.flight.departure_time}。我们已将预订详情发送到您的邮箱 {booking.passenger_email}。"
                else:
                    return "抱歉，预订过程中出现错误，请重试。"

            # 合并信息
            merged_info = {}

            # 先从当前预订中获取已有信息
            if current_booking:
                merged_info = {
                    'source_city': current_booking.source_city.name if current_booking.source_city else None,
                    'destination_city': current_booking.destination_city.name if current_booking.destination_city else None,
                    'departure_date': current_booking.departure_date,
                    'passenger_name': current_booking.passenger_name,
                    'passenger_email': current_booking.passenger_email,
                    'passenger_phone': current_booking.passenger_phone,
                    'selected_flight_id': current_booking.selected_flight_id,
                    'booking_stage': current_booking.booking_stage,
                    'preferred_time': current_booking.preferred_time
                }
                logger.info(f"Current info from booking: {merged_info}")

            # 用新信息更新，但只更新非空值
            for key, value in new_info.items():
                if value is not None:  # 只有当新值非空时才更新
                    merged_info[key] = value

            # 修复键名错误
            if 'passger_email' in merged_info:
                merged_info['passenger_email'] = merged_info.pop('passger_email')
            if 'passener_email' in merged_info:
                merged_info['passenger_email'] = merged_info.pop('passener_email')

            logger.info(f"Final merged info (after key correction): {merged_info}")

            # 保存合并后的信息
            saved = self._save_to_temp_booking(merged_info)
            if not saved:
                logger.error("Failed to save booking info")
                return "Sorry, there was an error saving your booking information."

            # 获取更新后的预订信息用于确认
            updated_booking = self._get_session_info()
            if not updated_booking:
                logger.error("Failed to retrieve updated booking")
                return "Sorry, there was an error retrieving your booking information."

            logger.info(
                f"Final booking state: source={updated_booking.source_city}, destination={updated_booking.destination_city}, date={updated_booking.departure_date}")

            # 根据预订阶段处理不同逻辑
            if updated_booking.booking_stage == 'confirming':
                # 显示订单确认信息
                from .models import Flight
                try:
                    flight = Flight.objects.get(id=updated_booking.selected_flight_id)

                    # 确定时间段
                    time_period = ""
                    hour = flight.departure_time.hour
                    if 5 <= hour < 12:
                        time_period = "【上午】"
                    elif 12 <= hour < 18:
                        time_period = "【下午】"
                    else:
                        time_period = "【晚上】"

                    # 清理邮箱显示
                    clean_email = updated_booking.passenger_email
                    if clean_email and '@' in clean_email:
                        email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', clean_email)
                        if email_match:
                            clean_email = email_match.group(1)

                    return (
                        f"请确认您的订单信息:\n\n"
                        f"航班信息\n"
                        f"航班: {flight.airline.name} - {flight.id}\n"
                        f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                        f"日期: {flight.departure_date}\n"
                        f"时间: {time_period}{flight.departure_time}\n"
                        f"价格: ¥{flight.price}\n\n"
                        f"乘客信息\n"
                        f"乘客: {updated_booking.passenger_name}\n"
                        f"电子邮件: {clean_email}\n"
                        f"电话: {updated_booking.passenger_phone}\n\n"
                        f"请回复\"确认\"完成预订，或回复\"修改\"更改信息。"
                    )
                except Exception as e:
                    logger.error(f"Error retrieving flight details: {e}")
                    return "抱歉，获取航班详情时出错。请重试。"

            elif updated_booking.booking_stage == 'collecting_info':
                # 收集乘客信息
                missing_info = []
                if not updated_booking.passenger_name:
                    missing_info.append("姓名")

                # 检查邮箱有效性
                has_valid_email = False
                if updated_booking.passenger_email:
                    email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', updated_booking.passenger_email)
                    if email_match:
                        has_valid_email = True

                if not has_valid_email:
                    missing_info.append("电子邮件")

                if not updated_booking.passenger_phone:
                    missing_info.append("联系电话")

                if missing_info:
                    return f"请提供以下信息以完成预订: {', '.join(missing_info)}"
                else:
                    # 如果所有信息都已收集，更新到确认阶段
                    updated_booking.booking_stage = 'confirming'
                    updated_booking.save()
                    from .models import Flight
                    try:
                        flight = Flight.objects.get(id=updated_booking.selected_flight_id)

                        # 确定时间段
                        time_period = ""
                        hour = flight.departure_time.hour
                        if 5 <= hour < 12:
                            time_period = "【上午】"
                        elif 12 <= hour < 18:
                            time_period = "【下午】"
                        else:
                            time_period = "【晚上】"

                        # 清理邮箱显示
                        clean_email = updated_booking.passenger_email
                        if '@' in clean_email:
                            email_match = re.search(r'([\w\.-]+@[\w\.-]+\.\w+)', clean_email)
                            if email_match:
                                clean_email = email_match.group(1)

                        return (
                            f"请确认您的订单信息:\n\n"
                            f"航班信息\n"
                            f"航班: {flight.airline.name} - {flight.id}\n"
                            f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                            f"日期: {flight.departure_date}\n"
                            f"时间: {time_period}{flight.departure_time}\n"
                            f"价格: ¥{flight.price}\n\n"
                            f"乘客信息\n"
                            f"乘客: {updated_booking.passenger_name}\n"
                            f"电子邮件: {clean_email}\n"
                            f"电话: {updated_booking.passenger_phone}\n\n"
                            f"请回复\"确认\"完成预订，或回复\"修改\"更改信息。"
                        )
                    except Exception as e:
                        logger.error(f"Error retrieving flight details: {e}")
                        return "抱歉，获取航班详情时出错。请重试。"

            elif updated_booking.selected_flight_id:
                # 已选择航班但还未收集完所有信息
                return self._collect_passenger_info(updated_booking)

            # 如果所有必要信息都有了，返回航班搜索结果
            elif updated_booking.source_city and updated_booking.destination_city and updated_booking.departure_date:
                return self._search_flights(updated_booking)

            # 否则继续对话
            context = {
                'source_city': updated_booking.source_city.name if updated_booking.source_city else None,
                'destination_city': updated_booking.destination_city.name if updated_booking.destination_city else None,
                'date': updated_booking.departure_date.strftime('%Y-%m-%d') if updated_booking.departure_date else None,
                'booking_stage': updated_booking.booking_stage,
                'preferred_time': updated_booking.preferred_time
            }

            llm_response = self.llm_client.get_response(message, context)
            return llm_response.get('response', "Please provide more information.")

        except Exception as e:
            logger.error(f"Error in process_message: {e}")
            return "Sorry, there was a system error. Please try again."

    # 将以下方法添加到DialogManager类中

    def _extract_booking_query_params(self, message):
        """从消息中提取查询订单的参数"""
        info = {}

        # 提取订单编号
        booking_id_patterns = [
            r'(?:订单|预订|预定|机票|航班)[号码编]?[为是:：]\s*(\d+)',
            r'(?:order|booking|reservation)(?:\s+id|#|number|code)?[:\s]+(\d+)',
            r'[订单号码]\s*[#]?\s*(\d+)',
            r'#(\d+)',
            r'\b(\d{1,5})\b'  # 简单的数字，可能是订单号
        ]

        for pattern in booking_id_patterns:
            booking_id_match = re.search(pattern, message, re.IGNORECASE)
            if booking_id_match:
                info['booking_id'] = booking_id_match.group(1)
                logger.info(f"Found booking ID: {info['booking_id']}")
                break

        # 提取姓名（可能用于查询）
        if not info.get('booking_id'):
            name_pattern = r'(?:我叫|my name is|name[:\s]+|姓名[:\s]+|我的名字是|名字[是为:：\s]+)[\s:：]*([^\n,\.。，;；]+)'
            name_match = re.search(name_pattern, message, re.IGNORECASE)
            if name_match:
                info['passenger_name'] = name_match.group(1).strip()
                logger.info(f"Found passenger name for query: {info['passenger_name']}")

        # 提取邮箱（可能用于查询）
        if not info.get('booking_id'):
            email = self.extract_email(message)
            if email:
                info['passenger_email'] = email
                logger.info(f"Found email for query: {info['passenger_email']}")

        # 提取电话（可能用于查询）
        if not info.get('booking_id'):
            phone_pattern = r'(?:电话|phone|tel|联系方式|手机|联系电话|号码)[是为:：\s]*([0-9+\-\s]{8,})'
            phone_match = re.search(phone_pattern, message, re.IGNORECASE)
            if phone_match:
                info['passenger_phone'] = re.sub(r'\s+', '', phone_match.group(1).strip())
                logger.info(f"Found phone for query: {info['passenger_phone']}")
            elif re.search(r'\b\d{11}\b', message):  # 中国手机号
                info['passenger_phone'] = re.search(r'\b\d{11}\b', message).group(0)
                logger.info(f"Found phone for query (direct): {info['passenger_phone']}")

        # 检查操作意图
        if '取消' in message or 'cancel' in message.lower():
            info['operation'] = 'cancel'
            logger.info("User intent: cancel booking")
        elif '修改' in message or 'change' in message.lower() or 'modify' in message.lower() or 'update' in message.lower():
            info['operation'] = 'update'
            logger.info("User intent: update booking")
        elif '查询' in message or '查找' in message or 'find' in message.lower() or 'search' in message.lower() or 'lookup' in message.lower():
            info['operation'] = 'find'
            logger.info("User intent: find booking")

        logger.info(f"Extracted booking query params: {info}")
        return info

    def _find_bookings(self, params):
        """根据参数查找预订"""
        try:
            from .models import Booking

            query = Booking.objects.all()

            if params.get('booking_id'):
                query = query.filter(id=params['booking_id'])

            if params.get('passenger_name'):
                query = query.filter(passenger_name__icontains=params['passenger_name'])

            if params.get('passenger_email'):
                query = query.filter(passenger_email__iexact=params['passenger_email'])

            if params.get('passenger_phone'):
                query = query.filter(passenger_phone__iexact=params['passenger_phone'])

            bookings = query.select_related('flight', 'flight__airline', 'flight__route',
                                            'flight__route__source_city', 'flight__route__destination_city')

            return bookings
        except Exception as e:
            logger.error(f"Error finding bookings: {e}")
            return []

    def _handle_booking_query(self, message):
        """处理用户查询、修改或取消预订的请求"""
        query_params = self._extract_booking_query_params(message)

        if not query_params:
            return "请提供订单编号、预订人姓名、联系电话或邮箱，以便我帮您查询预订信息。"

        bookings = self._find_bookings(query_params)

        if not bookings.exists():
            return "抱歉，未找到符合条件的预订。请确认您提供的信息是否正确。"

        # 如果找到多个预订，先列出所有预订让用户选择
        if bookings.count() > 1:
            response = f"找到了 {bookings.count()} 个符合条件的预订:\n\n"

            for i, booking in enumerate(bookings, 1):
                flight = booking.flight

                # 确定时间段
                time_period = ""
                hour = flight.departure_time.hour
                if 5 <= hour < 12:
                    time_period = "【上午】"
                elif 12 <= hour < 18:
                    time_period = "【下午】"
                else:
                    time_period = "【晚上】"

                response += (
                    f"订单 {i}:\n"
                    f"订单编号: {booking.id}\n"
                    f"航班: {flight.airline.name} - {flight.id}\n"
                    f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                    f"日期: {flight.departure_date}\n"
                    f"时间: {time_period}{flight.departure_time}\n"
                    f"乘客: {booking.passenger_name}\n"
                    f"状态: {self._get_status_display(booking.status)}\n\n"
                )

            response += "请通过订单编号指定您要操作的预订。例如: '取消订单 #12345' 或 '修改订单 #12345'"
            return response

        # 只有一个预订，直接处理
        booking = bookings.first()
        flight = booking.flight

        # 确定时间段
        time_period = ""
        hour = flight.departure_time.hour
        if 5 <= hour < 12:
            time_period = "【上午】"
        elif 12 <= hour < 18:
            time_period = "【下午】"
        else:
            time_period = "【晚上】"

        if query_params.get('operation') == 'cancel':
            # 处理取消预订
            if booking.status == 'cancelled':
                return f"订单 #{booking.id} 已经被取消，无需重复操作。"

            booking.status = 'cancelled'
            booking.save()

            return (
                f"已成功取消订单 #{booking.id}\n\n"
                f"取消的预订信息:\n"
                f"航班: {flight.airline.name} - {flight.id}\n"
                f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                f"日期: {flight.departure_date}\n"
                f"时间: {time_period}{flight.departure_time}\n"
                f"乘客: {booking.passenger_name}"
            )

        elif query_params.get('operation') == 'update':
            # 设置状态为修改模式
            self._set_modification_mode(booking.id)

            # 返回当前预订信息和修改指南
            return (
                f"您正在修改订单 #{booking.id}，当前预订信息如下:\n\n"
                f"航班: {flight.airline.name} - {flight.id}\n"
                f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                f"日期: {flight.departure_date}\n"
                f"时间: {time_period}{flight.departure_time}\n"
                f"乘客: {booking.passenger_name}\n"
                f"电子邮件: {booking.passenger_email}\n"
                f"电话: {booking.passenger_phone}\n\n"
                f"您可以修改以下信息:\n"
                f"1. 乘客姓名: 例如「修改姓名为张三」\n"
                f"2. 联系邮箱: 例如「修改邮箱为example@email.com」\n"
                f"3. 联系电话: 例如「修改电话为13800138000」\n\n"
                f"如果要重新搜索航班，请回复「重新选择航班」。\n"
                f"完成修改后，请回复「完成修改」。\n"
                f"取消修改请回复「取消修改」。"
            )

        else:  # 默认为查询操作
            # 返回预订详情
            return (
                f"订单 #{booking.id} 的详细信息:\n\n"
                f"航班: {flight.airline.name} - {flight.id}\n"
                f"路线: {flight.route.source_city.name} → {flight.route.destination_city.name}\n"
                f"日期: {flight.departure_date}\n"
                f"时间: {time_period}{flight.departure_time}\n"
                f"乘客: {booking.passenger_name}\n"
                f"电子邮件: {booking.passenger_email}\n"
                f"电话: {booking.passenger_phone}\n"
                f"状态: {self._get_status_display(booking.status)}\n\n"
                f"如需修改此预订，请回复「修改此订单」。\n"
                f"如需取消此预订，请回复「取消此订单」。"
            )

    def _get_status_display(self, status):
        """获取状态的中文显示"""
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消'
        }
        return status_map.get(status, status)

    def _set_modification_mode(self, booking_id):
        """设置会话为修改模式"""
        try:
            from .models import TempBooking

            # 获取当前预订
            current_booking = self._get_session_info()
            if not current_booking:
                return False

            # 标记为修改模式
            current_booking.booking_stage = 'modifying'
            # 保存要修改的预订ID
            current_booking.modification_id = booking_id
            current_booking.save()

            logger.info(f"Set session {self.session_id} to modification mode for booking {booking_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting modification mode: {e}")
            return False

    def _handle_booking_modification(self, message, current_booking):
        """处理预订修改流程"""
        try:
            from .models import Booking

            # 获取要修改的预订
            try:
                booking_to_modify = Booking.objects.get(id=current_booking.modification_id)
            except Booking.DoesNotExist:
                logger.error(f"Booking to modify not found: {current_booking.modification_id}")
                return "抱歉，找不到要修改的预订。请重新开始。"

            # 处理取消修改
            if '取消修改' in message or 'cancel modification' in message.lower():
                current_booking.booking_stage = 'searching'  # 重置状态
                current_booking.modification_id = None
                current_booking.save()
                return "已取消修改，返回正常预订流程。"

            # 处理完成修改
            if '完成修改' in message or '完成' in message or 'done' in message.lower() or 'finish' in message.lower():
                current_booking.booking_stage = 'searching'  # 重置状态
                current_booking.modification_id = None
                current_booking.save()
                return f"订单 #{booking_to_modify.id} 已成功更新。"

            # 提取新信息
            info = self._extract_info_from_message(message)
            updated = False

            # 更新姓名
            if info.get('passenger_name'):
                booking_to_modify.passenger_name = info['passenger_name']
                updated = True
                logger.info(f"Updated booking {booking_to_modify.id} name to: {info['passenger_name']}")

            # 更新邮箱
            if info.get('passenger_email'):
                booking_to_modify.passenger_email = info['passenger_email']
                updated = True
                logger.info(f"Updated booking {booking_to_modify.id} email to: {info['passenger_email']}")

            # 更新电话
            if info.get('passenger_phone'):
                booking_to_modify.passenger_phone = info['passenger_phone']
                updated = True
                logger.info(f"Updated booking {booking_to_modify.id} phone to: {info['passenger_phone']}")

            if updated:
                booking_to_modify.save()
                return f"已更新订单 #{booking_to_modify.id} 的信息。\n\n您还需要修改其他信息吗？完成后请回复「完成修改」。"
            else:
                return "未检测到需要修改的信息。您可以修改姓名、邮箱或电话。例如「修改姓名为张三」。"

        except Exception as e:
            logger.error(f"Error handling booking modification: {e}")
            return "抱歉，修改订单时出错。请重试。"