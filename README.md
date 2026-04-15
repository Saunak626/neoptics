
# NeoOptics 项目环境与目标

# 项目目标

NeoOptics 项目旨在对新生儿手腕进行红光和近红外光学蒙特卡洛仿真，主要任务包括：

1. 构建新生儿手腕分层体素模型，包括皮肤、脂肪、血管和骨组织。
2. 设置不同波长（红光、近红外）的光源参数。
3. 使用 MCX CUDA 内核通过 Python (`pmcx`) 发起仿真，生成 photon trajectory 和 fluence 分布。
4. 在 Python 中可视化体素结构、光子轨迹及能量分布，用于分析红光与近红外在组织中的传播差异。
5. 为后续科研实验提供可重复、可参数化的仿真基础。

# 环境依赖

- 操作系统：Windows 10/11
- Python 版本：3.10（官方推荐，3.11 可尝试，3.12 可能不兼容）
- GPU：NVIDIA CUDA-capable GPU（推荐 RTX 系列，驱动需支持 CUDA 12.4）
- Python 包：
  - `pmcx`：MCX Python binding，用于仿真控制
  - `numpy`：数组与体素数据处理
  - `matplotlib`：2D 数据可视化
  - `pyvista`：3D fluence 和 photon trajectory 可视化

```
# 创建环境（Python 3.12）
conda create -n neoptics python=3.12 -y

# 激活环境
conda activate neoptics

# 安装 pmcx（官方 MCX Python binding）
pip install pmcx

# 安装可视化包
pip install numpy matplotlib pyvista

```

