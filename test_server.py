import requests
import json
import sys
import uuid

BASE_URL = "http://localhost:8000"  # 服务器地址

def test_root():
    """测试根路径"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print("\n=== 测试根路径 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"错误: {e}")

def test_health():
    """测试健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print("\n=== 测试健康检查 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"错误: {e}")

def test_debate_sample():
    """测试获取示例输入数据"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/debate/sample")
        print("\n=== 测试获取示例输入 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"错误: {e}")
        return None

def test_debate(sample_data=None):
    """测试debate端点"""
    if not sample_data:
        print("\n=== 跳过测试debate端点（无示例数据）===")
        return
    
    try:
        # 构造符合 RequestBase 模型的请求数据
        request_data = {
            "request_id": str(uuid.uuid4()),  # 生成唯一的请求ID
            "data": sample_data
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/debate",
            json=request_data
        )
        print("\n=== 测试debate端点 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"错误: {e}")

def main():
    """主函数"""
    print("开始测试服务器...")
    
    # 测试基本端点
    test_root()
    test_health()
    
    # 获取示例数据并测试debate端点
    sample_data = test_debate_sample()
    test_debate(sample_data)
    
    print("\n测试完成！")

if __name__ == "__main__":
    main() 