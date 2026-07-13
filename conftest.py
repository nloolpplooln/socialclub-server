"""确保测试从项目根导入 app 包。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
