# FAST-Calib 单次标定使用教程

本教程将指导你如何使用 `fast_calib` 进行单次 LiDAR 与相机的联合标定。

## 1. 数据录制 (Rosbag)

在进行标定前，需要录制包含传感器数据的 rosbag。请确保标定过程中**保持传感器和标定板静止**。

### 录制要求
- **必须包含的话题**：
  - **LiDAR 点云**：`sensor_msgs/PointCloud2` 或 `livox_ros_driver/CustomMsg` (例如 `/livox/lidar`, `/hesai/pandar`)
  - **相机图像**：`sensor_msgs/Image` 或 `sensor_msgs/CompressedImage` (例如 `/camera/image_color`, `/usb_cam/image_raw`)
- **时长**：录制 5-10 秒即可。

**录制命令示例**：
```bash
rosbag record /livox/lidar /camera/image_color -O calib_data/my_calib.bag
```

---

## 2. 参数配置与准备工作

所有的配置都在 `config/qr_params.yaml` 文件中进行。你需要根据你的硬件和场景修改以下几组参数。

### A. 相机模型与内参 (Camera Intrinsics)
你需要提供相机的标定参数。如果你的相机还没有标定内参，请先使用 ROS 自带的 `camera_calibration` 或其他工具获取内参。

*   **`cam_model`**: 相机模型类型，通常为 `"pinhole"` (针孔) 或 `"fisheye"` (鱼眼)。
*   **`fx`, `fy`**: 焦距 (像素单位)。
*   **`cx`, `cy`**: 主点坐标 (图像中心)。
*   **`k1`, `k2`, `p1`, `p2`**: 畸变系数 (对应 OpenCV 标准)。如果是鱼眼模型，还需填写 `k3`, `k4`。

### B. 标定板参数 (Calibration Target)
根据你打印或制作的标定板实际尺寸填写。单位均为**米 (m)**。

*   **`marker_size`**: 二维码或 ArUco 码的黑色边长。
*   **`circle_radius`**: 圆形特征的半径（如果是圆形标定板）。
*   **`delta_width/height...`**: 多个标记中心之间的水平/垂直距离。

### C. 距离过滤 (Distance Filter)
这是标定成功的关键步骤。我们需要过滤掉背景环境，只保留标定板周围的点云。

**工具脚本**：`scripts/distance_filter_tool.py`

**使用方法**：
1.  运行脚本（会自动读取 bag 中的点云）：
    ```bash
    # 语法：python3 scripts/distance_filter_tool.py [bag路径]
    python3 scripts/distance_filter_tool.py calib_data/my_calib.bag
    ```
2.  **交互选点 (Open3D)**：
    *   脚本会弹出一个可视化窗口。
    *   **操作**：按住 **Shift 键** + **鼠标左键** 点击点云。
    *   **选点原则**：在标定板的**上、下、左、右**周围空间各点一下（至少 4 个点），形成一个包围标定板的区域。
    *   选好后按 **Q 键** 退出。
3.  **获取结果**：
    *   脚本会在 bag 同目录下生成一个 `.txt` 文件 (例如 `my_calib.txt`)。
    *   打开该文件，复制里面的 `x_min`, `x_max`, `y_min`... 等 6 个值。
4.  **修改配置**：
    *   将这 6 个值填入 `config/qr_params.yaml` 的 **Distance filter** 部分。

### D. 提取标定图像
标定程序需要读取一张静态图片，而不是直接订阅图像流。

**工具脚本**：`scripts/extract_image_from_bag.py`

**使用方法**：
1.  运行脚本从 bag 中提取图片：
    ```bash
    # 语法：python3 scripts/extract_image_from_bag.py [bag路径]
    python3 scripts/extract_image_from_bag.py calib_data/my_calib.bag
    ```
    *   脚本会自动检测图像话题。
    *   默认提取前 5 帧（每秒 1 帧），保存在 bag 同目录下，文件名为 `my_calib_1.png`, `my_calib_2.png` 等。
2.  **选择图片**：
    *   查看生成的图片，选择一张**清晰、无模糊、标定板完整**的图片。
3.  **修改配置**：
    *   在 `config/qr_params.yaml` 中修改 `image_path`：
        ```yaml
        image_path: "$(find fast_calib)/calib_data/my_calib_1.png"
        ```

### E. 输入路径设置
最后，确认 `config/qr_params.yaml` 底部的输入路径正确：

*   **`lidar_topic`**: 修改为你录制的雷达话题名 (如 `/livox/lidar` 或 `/hesai/pandar`)。
*   **`bag_path`**: 指向你的 `.bag` 文件路径。
*   **`image_path`**: 指向你刚才提取的 `.png` 图片路径。

---

## 3. 运行标定

1.  **启动环境**：
    打开终端，进入你的工作空间：
    ```bash
    cd ~/catkin_ws
    source devel/setup.bash
    ```

2.  **启动标定程序**：
    不需要手动运行 `roscore`，`roslaunch` 会自动处理。
    ```bash
    roslaunch fast_calib calib.launch
    ```

3.  **查看过程**：
    *   程序启动后会打开 **RViz**。
    *   你应该能看到雷达点云（白色）和检测到的标定板平面（绿色/红色）。
    *   终端会输出检测进度和计算结果。

---

## 4. 输出结果与验证

标定完成后，结果会保存在 `config/qr_params.yaml` 中指定的 `output_path` 目录（默认为 `output/`）。

### 输出文件说明
*   **`single_calib_result.txt`**: 包含最终的标定结果。
    *   **Extrinsic (R, t)**: 相机到雷达的旋转矩阵和平移向量。
    *   这些数值可以直接用于你的传感器融合程序或后续的 yaml 配置文件。
*   **`colored_cloud.pcd`**: 融合后的彩色点云。
    *   可以使用 `pcl_viewer` 或其他点云工具打开，检查颜色是否准确对齐到物体上（验证标定精度）。

### 常见问题
*   **Q: 找不到标定板？**
    *   A: 检查 `Distance Filter` 的范围是否正确包围了标定板，且没有包含过多的背景墙面。
*   **Q: 图像加载失败？**
    *   A: 检查 `image_path` 路径是否正确，确保是绝对路径或使用了 `$(find fast_calib)` 前缀。

