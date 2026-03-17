import asyncio
from app.database.db import (
    connect_db, disconnect_db, 
    create_session, save_detection, get_session_history
)

async def test_workflow():
    print("--- Connecting to Database ---")
    await connect_db()
    
    try:
        # 1. ทดสอบสร้าง Session
        print("\n1. Testing Create Session...")
        sess_id = await create_session(device_info="MacBook Pro - Chrome")
        print(f"Success! Session ID: {sess_id}")
        
        # 2. ทดสอบบันทึกการตรวจจับ (Simulate YOLO result)
        print("\n2. Testing Save Detection...")
        species = "Hilsa Shad"
        conf = 0.985
        bbox = [100, 200, 50, 80] # [x, y, w, h]
        
        await save_detection(
            session_id=sess_id,
            species=species,
            confidence=conf,
            bbox=bbox,
            image_path="static/outputs/test_fish.jpg"
        )
        print("Success! Detection saved.")
        
        # 3. ทดสอบดึงข้อมูลประวัติ
        print("\n3. Testing Get History...")
        history = await get_session_history(sess_id)
        for record in history:
            print(f"Found: {record['species_name']} with confidence {record['confidence']}")
            
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("\n--- Disconnecting ---")
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(test_workflow())