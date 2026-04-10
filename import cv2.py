import cv2 #thu vien cv2

cap = cv2.VideoCapture(1) #tạo biến cap, bật cam mặc định và lưu các giá trị vào biến cap

while True: #vòng lặp vo hạn
    ret, frame = cap.read() # chụp ảnh/lấy giá trị từ biến cap xong trích ra thành ret(đọc thành công hay không) và frame (ma trận ảnh)
    print(frame.shape)
    cv2.imshow("Camera", frame) # bật tap camera show liên tục ảnh nên tạo thành video
    print(frame[0,0])
    frame[0:100, 0:100] = [0, 0, 255]
    if cv2.waitKey(1) & 0xFF == ord('q'): # kiểm tra liên tục xem phím q có được bấm ko, bấm q để dừng
        break

cap.release()
cv2.destroyAllWindows()