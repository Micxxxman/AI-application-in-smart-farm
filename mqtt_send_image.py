import paho.mqtt.client as mqtt
import requests
import time
import cv2
from ultralytics import YOLO
from picamera2 import Picamera2
piCam = Picamera2()
import time
import threading
import json
from datetime import datetime
now = datetime.now()
width = 0
hight = 0
global add_area
add_area=0
old_avg_area =0
max_i = 1
data_work =True
stop_camrea = True
#piCam = Picamera2()
W=1280
H=720
RES = (W,H)
piCam.preview_configuration.main.size = RES
piCam.preview_configuration.main.format = "RGB888"
piCam.preview_configuration.controls.FrameRate=60
piCam.preview_configuration.align()
piCam.configure("preview")
piCam.start()

send_mqtt_plant = {"CONNECT":"MQTT","topic":"222226/20251104/led_ctl","plant_zoom":"A","layout":"1","red":"80","blue":"80","white":"80","start":"9","close":"18","odj":"LED"}


send_mqtt_speeding = { "CONNECT":"MQTT","topic":"222226/20251104/led_ctl","plant_zoom":"A","layout":"1","red":"50","blue":"50","white":"10","start":"9","close":"18","odj":"LED"}
# Load the exported NCNN model (replace with your model path)
#model = YOLO("/home/pjm/yolo11n_ncnn_model", task = 'detect')
model = YOLO("/home/pi/model/my_model.pt", task = 'detect')

fps=0
tStart=time.time()
#def cout_area(results):
# Set resolution for faster processing (optional, adjust based on your needs)
area = 0

# Configuration
broker = "61.238.107.202"
port = 1883
topic = "222226/20251104/led_ctl"
stop_event = threading.Event()


# 伺服器端點 (替換為您的伺服器URL)
rtsp_urls = [
    "rtsp://admin:23909654Mic@192.168.50.218:554",
]
SERVER_URL = "http://61.238.107.202:8081/upload"

# 抓取間隔(秒)
CAPTURE_INTERVAL = 0.01 

activa_ = True
internet_status = True
get_commad =False



def is_internt_on(url='http://www.google.com/',timeout = 5):
    try:
        # Use HEAD request for speed
#        requests.head(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        return False


# Callback when connected
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(topic)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata,msg):
    print(f"Received message:{msg.topic} {msg.payload.decode()}")
    global stop_camrea
    stop_camrea=True
    if msg.payload.decode() == "cam_test":

     capture_and_send(0,rtsp_urls[0])
     activa_=False
# Initialize client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
# Connect to broker
client.connect(broker, port, 60)
# Start loop to handle network traffic/reconnects in background
client.loop_start()



 


'''capture and send frame'''
def capture_and_send(camera_id,rtsp_url):
    global width
    global height
    global width_p
    global height_p
    global add_area
    global avg_area
    global old_avg_area
    global stop_camrea
    fps = 10
    interval = 1.0 / fps
    try:
        couter = 0
        while stop_camrea:
#            print(couter)
            couter = couter+1
            if couter > 20:
             stop_camrea=False
             break
             couter = 0
             
            # 讀取一幀
            start_time = time.time()
            frame= piCam.capture_array()
            results = model(frame, conf=0.05, verbose=False)
            box = results[0].boxes
            activa_=False
            frame = results[0].plot()  # Plots old boxes on new frame!
            
            for i, box in enumerate(results[0].boxes):
            # Get coordinates (xyxy: xmin, ymin, xmax, ymax)
                coords = box.xyxy[0].tolist()
                x1, y1, x2, y2 = [round(c) for c in coords]
                
                # Calculate dimension
                width = x2 - x1
                height = y2 - y1
                
                width_p = x2 + x1
                height_p = y2 + y1
                
                # Get class and confidence
                cls = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                name = model.names[cls]
                area = width*height
                add_area = add_area + area
                max_i = i+1
                if area > 60950:
                 cv2.putText(frame, "plant", (int(width_p*0.4), int(height_p*0.4)), 
                    cv2.FONT_HERSHEY_SIMPLEX, H*.002, (0, 0, 255),2)
                 
                 
                 #print("plant")
                if area < 38612:
                 #print("seeding")
                 cv2.putText(frame, "seeding", (int(width_p*0.4), int(height_p*0.4)), 
                    cv2.FONT_HERSHEY_SIMPLEX, H*.002, (0, 0, 255), 2)
                 
               
                 
                print(f"Object {i+1}: {name} ({conf:.2f}) | "
                      f"Box: ({x1}, {y1}) to ({x2}, {y2}) | "
                      f"Dim: {width}x{height}")

            avg_area = add_area
 #           print(add_area)
            
            if abs(avg_area -old_avg_area) > 1000:
             if avg_area > 60950:
                client.publish(topic,json.dumps(send_mqtt_plant) )
                print("plant")
             if avg_area < 38612:
                client.publish(topic,json.dumps(send_mqtt_speeding) )
                print("seeding")
            old_avg_area = avg_area 
            add_area = 0
            
            frame = cv2.resize(frame, (400, 400))
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = buffer.tobytes()
            try:
                # payload = 
                # 發送到伺服器
                SERVER_URL_id = SERVER_URL +"/222226/20251104/"+str(7)
                response = requests.post(
                    SERVER_URL_id,
                    data=jpg_as_text
                )
                if response.status_code == 200:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 影像發送成功")
                else:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 伺服器返回錯誤:")
            except requests.exceptions.RequestException as e:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 發送失敗:")
            # 等待指定間隔
            elapsed = time.time() - start_time
            if elapsed < interval:
             time.sleep(interval - elapsed)    
    except KeyboardInterrupt:
        print("停止抓取...")
    finally:
        #cap.release()
        activa_=True
        


# Keep main thread alive
try:
    while True:
        #//client.publish(topic, "Keeping connection alive")
       # print("Published message")
        if now.strftime("%H") == 9 and data_work:
           capture_and_send(0,rtsp_urls[0])
           data_work = False
        else:
           data_work = True
        if get_commad == False:
            if is_internt_on() == False:
                internet_status =False
            if is_internt_on() and internet_status == False:
                # Initialize client
                client = mqtt.Client()
                client.on_connect = on_connect
                client.on_message = on_message
                # Connect to broker
                client.connect(broker, port, 60)
                # Start loop to handle network traffic/reconnects in background
                client.loop_start()
        time.sleep(0.1) # Publish every 10 seconds
        #break
except KeyboardInterrupt:
    print("Exiting...")
    client.loop_stop()
    client.disconnect()
