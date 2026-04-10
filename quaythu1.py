import mediapipe
print(mediapipe)
print(mediapipe.__file__)

#gọi mấy cái thư viện 
import cv2
import mediapipe as mp
import csv
import time

mp_pose = mp.solutions.pose #truy cập module pose của medpipe
cap = cv2.VideoCapture(1)

file = open("arm_data.csv", mode='w', newline='') #tạo mới file để ghi dữ liệu vô
writer = csv.writer(file) #xuống dòng các kiểu cho file csv
#tạo các cột để dữ liệu chạy vô
writer.writerow([
    "frame", "timestamp",
    "shoulder_x", "shoulder_y", "shoulder_z", "shoulder_visibility",
    "elbow_x", "elbow_y", "elbow_z", "elbow_visibility",
    "wrist_x", "wrist_y", "wrist_z", "wrist_visibility"
])

frame_count = 0
start_time = time.time() #tính thời gian kể từ năm 1970 để mang ra trừ thời gian mỗi loop
                #AI check xem phải người ko và thu dữ liệu, nếu dưới 50% thì ko thu
with mp_pose.Pose(min_detection_confidence=0.5,
                  min_tracking_confidence=0.5) as pose:

    while cap.isOpened(): # chạy liên tục tới khi cam đóng
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = time.time() - start_time # thời gian trôi kể từ lúc bắt đầu thu, dựa vào cái ở trên ra rất chính xác

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # đổi từ BGR sang RGB
        results = pose.process(image) # tạo biến result là ảnh trả về

        if results.pose_landmarks:# bước này kiểm tra xem ảnh có phát hiện người thật ở trong không
            landmarks = results.pose_landmarks.landmark #tạo biến có kho 33 điểm ảnh được lưu của medpipe
            #lấy lần lượt vai phải, khủy tay phải và cổ tay phải
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            # ghi dữ liệu vào file csv mỗi vòng lặp 1 dòng
            writer.writerow([
                frame_count, timestamp,
                shoulder.x, shoulder.y, shoulder.z, shoulder.visibility,
                elbow.x, elbow.y, elbow.z, elbow.visibility,
                wrist.x, wrist.y, wrist.z, wrist.visibility
            ])

            frame_count += 1 # chuẩn bị cho frame sau

        cv2.imshow("Collecting Data", frame) # hiển thị video cho biết camera đang chạy

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
file.close()
cv2.destroyAllWindows()