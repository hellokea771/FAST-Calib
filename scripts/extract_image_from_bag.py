#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能：从 rosbag 中提取图像并保存为 PNG 文件。
用法：
    python3 extract_image_from_bag.py <bag_file> <output_dir> [image_topic]

默认图像 topic 为 /camera/image_color，如需更改请作为第三个参数传入，
或者脚本会自动检测 bag 中的图像 topic。
"""

import os
import sys
import cv2
import rosbag
import numpy as np
from cv_bridge import CvBridge

def extract_image(bag_file, output_dir, target_topic=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[Info] 创建输出目录: {output_dir}")

    bridge = CvBridge()
    bag = rosbag.Bag(bag_file, "r")
    
    # 自动检测图像 topic
    image_topics = []
    if target_topic is None:
        print(f"[Info] 正在扫描 bag 文件中的图像 topic...")
        types = []
        topics = []
        for topic, msg, t in bag.read_messages():
            if msg._type == "sensor_msgs/Image" or msg._type == "sensor_msgs/CompressedImage":
                if topic not in topics:
                    topics.append(topic)
                    types.append(msg._type)
                    print(f"       发现图像 topic: {topic} (type: {msg._type})")
        
        if len(topics) == 0:
            print("[Error] 未在 bag 中找到图像 topic！")
            bag.close()
            return
        elif len(topics) == 1:
            target_topic = topics[0]
            print(f"[Info] 自动选择 topic: {target_topic}")
        else:
            target_topic = topics[0]
            print(f"[Info] 发现多个图像 topic，默认选择第一个: {target_topic}")
            print(f"       如果你想要其他的，请在命令行指定 topic 名称。")

    print(f"[Info] 开始从 topic '{target_topic}' 提取图像 (每隔1秒提取一帧，共5帧)...")
    
    # 配置提取参数
    TARGET_FRAME_COUNT = 5
    TIME_INTERVAL = 1.0  # 间隔时间（秒）
    
    saved_count = 0
    last_timestamp = 0.0
    
    bag_name = os.path.splitext(os.path.basename(bag_file))[0]

    for topic, msg, t in bag.read_messages(topics=[target_topic]):
        if saved_count >= TARGET_FRAME_COUNT:
            break

        # 获取当前消息的时间戳 (秒)
        current_timestamp = t.to_sec()
        
        # 如果不是第一帧，且距离上一帧时间不足 1 秒，则跳过
        if saved_count > 0 and (current_timestamp - last_timestamp) < TIME_INTERVAL:
            continue

        try:
            cv_image = None
            if msg._type == "sensor_msgs/Image":
                # 尝试不同的编码转换
                try:
                    cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
                except:
                    try:
                        cv_image = bridge.imgmsg_to_cv2(msg, "rgb8")
                        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
                    except Exception as e:
                        print(f"[Error] 转换图像失败: {e}")
                        continue
                        
            elif msg._type == "sensor_msgs/CompressedImage":
                np_arr = np.frombuffer(msg.data, np.uint8)
                cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if cv_image is not None:
                output_filename = f"{bag_name}_{saved_count + 1}.png"
                output_path = os.path.join(output_dir, output_filename)
                
                cv2.imwrite(output_path, cv_image)
                print(f"[Success] 已保存第 {saved_count + 1} 帧到: {output_path} (时间戳: {current_timestamp:.2f})")
                
                saved_count += 1
                last_timestamp = current_timestamp
                
        except Exception as e:
            print(f"[Error] 处理图像帧失败: {e}")
            continue

    bag.close()
    
    if saved_count == 0:
        print(f"[Warn] 未能从 topic '{target_topic}' 提取到任何图像。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_image_from_bag.py <bag_file> [output_dir] [image_topic]")
        sys.exit(1)

    bag_path = sys.argv[1]
    
    # 输出目录默认为 bag 文件所在目录
    if len(sys.argv) > 2:
        out_dir = sys.argv[2]
    else:
        out_dir = os.path.dirname(os.path.abspath(bag_path))
        print(f"[Info] 未指定输出目录，默认使用: {out_dir}")

    target_topic = None
    if len(sys.argv) > 3:
        target_topic = sys.argv[3]

    if not os.path.isfile(bag_path):
        print(f"[Error] Bag 文件不存在: {bag_path}")
        sys.exit(1)

    extract_image(bag_path, out_dir, target_topic)

