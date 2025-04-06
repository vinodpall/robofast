from app.database.database import SessionLocal
from app.models import models
from datetime import datetime, timedelta

def create_test_data():
    db = SessionLocal()
    try:
        # 创建机器人数据
        robots = [
            models.Robot(
                name="智能机器人A1",
                robot_type="第一代",
                industry_type="工业机器人",
                product_series="外骨骼系列",
                price=10000.0,
                serial_number="89757-001",
                create_date="202503201900",
                status="在线",
                training_status="上线",
                skills="焊接,搬运,组装",
                awards="最佳工业机器人奖,创新设计奖",
                product_location="上海",
                dimensions="1800mm x 800mm x 600mm",
                image_url="https://example.com/robot1.jpg",
                remarks="第一代智能工业机器人",
                is_active=True
            ),
            models.Robot(
                name="协作机器人B2",
                robot_type="第二代",
                industry_type="协作机器人",
                product_series="灵活臂系列",
                price=15000.0,
                serial_number="89757-002",
                create_date="202503201901",
                status="在线",
                training_status="培训中",
                skills="精密装配,质量检测",
                awards="年度最佳协作机器人",
                product_location="北京",
                dimensions="1500mm x 600mm x 500mm",
                image_url="https://example.com/robot2.jpg",
                remarks="新一代协作机器人",
                is_active=True
            )
        ]
        db.add_all(robots)
        db.commit()

        # 创建训练场数据
        training_fields = [
            models.TrainingField(
                name="工业机器人训练中心",
                description="专业的工业机器人训练基地，配备先进的训练设备",
                image_url="https://example.com/field1.jpg",
                create_time=datetime.now()
            ),
            models.TrainingField(
                name="协作机器人实验室",
                description="面向未来的协作机器人训练场地",
                image_url="https://example.com/field2.jpg",
                create_time=datetime.now()
            )
        ]
        db.add_all(training_fields)
        db.commit()

        # 创建公司数据
        companies = [
            models.Company(
                name="未来机器人科技有限公司",
                description="专注于工业机器人研发与制造",
                address="上海市浦东新区科技园区",
                contact="021-12345678",
                create_time=datetime.now(),
                expiry_time=datetime.now() + timedelta(days=365)
            ),
            models.Company(
                name="智能协作机器人有限公司",
                description="致力于协作机器人解决方案",
                address="北京市海淀区科技园",
                contact="010-87654321",
                create_time=datetime.now(),
                expiry_time=datetime.now() + timedelta(days=365)
            )
        ]
        db.add_all(companies)
        db.commit()

        # 创建荣誉证书数据
        awards = [
            models.Award(
                name="2025年度最佳工业机器人",
                description="在工业自动化领域的突出贡献",
                issue_date=datetime.now() - timedelta(days=30),
                image_url="https://example.com/award1.jpg",
                create_time=datetime.now()
            ),
            models.Award(
                name="机器人创新设计金奖",
                description="在机器人创新设计方面的卓越成就",
                issue_date=datetime.now() - timedelta(days=60),
                image_url="https://example.com/award2.jpg",
                create_time=datetime.now()
            )
        ]
        db.add_all(awards)
        db.commit()

        # 创建视频数据
        videos = [
            models.Video(
                title="工业机器人操作演示",
                url="https://example.com/video1.mp4",
                type="本地视频",
                description="详细展示工业机器人的操作流程",
                create_time=datetime.now()
            ),
            models.Video(
                title="协作机器人实时工作",
                url="rtsp://example.com/stream1",
                type="在线流",
                description="展示协作机器人的实时工作状态",
                create_time=datetime.now()
            )
        ]
        db.add_all(videos)
        db.commit()

        # 创建参观记录数据
        visitor_records = [
            models.VisitorRecord(
                visit_date=datetime.now() - timedelta(days=1),
                visitor_count=50,
                create_time=datetime.now()
            ),
            models.VisitorRecord(
                visit_date=datetime.now() - timedelta(days=2),
                visitor_count=45,
                create_time=datetime.now()
            )
        ]
        db.add_all(visitor_records)
        db.commit()

        # 创建数据类型数据
        data_types = [
            models.DataType(
                name="温度传感器数据",
                description="机器人运行时的温度数据",
                unit="℃",
                create_time=datetime.now()
            ),
            models.DataType(
                name="能耗数据",
                description="机器人运行时的能耗数据",
                unit="kWh",
                create_time=datetime.now()
            )
        ]
        db.add_all(data_types)
        db.commit()

        # 创建数据记录数据
        data_records = [
            models.DataRecord(
                data_type_id=1,
                value="36.5",
                collect_time=datetime.now() - timedelta(hours=1),
                create_time=datetime.now()
            ),
            models.DataRecord(
                data_type_id=2,
                value="120.5",
                collect_time=datetime.now() - timedelta(hours=1),
                create_time=datetime.now()
            )
        ]
        db.add_all(data_records)
        db.commit()

        # 创建网页配置数据
        web_configs = [
            models.WebConfig(
                key="site_title",
                value="机器人训练营展示平台",
                description="网站标题配置",
                create_time=datetime.now()
            ),
            models.WebConfig(
                key="welcome_message",
                value="欢迎来到未来机器人世界",
                description="首页欢迎语配置",
                create_time=datetime.now()
            )
        ]
        db.add_all(web_configs)
        db.commit()

        print("测试数据创建成功！")

    except Exception as e:
        print(f"创建测试数据时出错: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data() 