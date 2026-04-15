# NeoOptics 实验目标需求文档

## 1. 文档目的

本文档用于定义 NeoOptics 项目的开发目标、实验范围、输入输出、功能需求、非功能需求、交付边界和验收标准。

本文件面向 CodeX，目标是让 CodeX 基于该文档完成第一阶段代码实现与测试。

## 2. 项目目标

项目目标是建立一个可复现、可参数化的 **新生儿 wrist-scale 组织光传播仿真框架**，用于比较：

- `530 nm` 绿光
- `660 nm` 红光
- `940 nm` 近红外

在下面两种工作模式下的差异：

- `reflectance`
- `transmittance`

需要重点回答的问题是：

1. 在新生儿 wrist-scale 尺度下，不同波长的光子主要采样哪些组织层。
2. 在反射模式下，哪种波长对浅层动脉更敏感。
3. 在透射模式下，660 nm 与 940 nm 的穿透和探测差异有多大。
4. 动脉深度、直径、脂肪厚度变化会如何影响探测信号。

## 3. 项目范围

## 3.1 本阶段必须实现

1. 体素化 wrist 模型生成
2. 三个波长的组织参数配置加载
3. 反射模式传感器配置生成
4. 透射模式传感器配置生成
5. PMCX 调用脚本
6. 单次仿真结果保存
7. 批量实验矩阵运行
8. 2D/3D 基础可视化
9. 最基本的结果汇总表

## 3.2 本阶段不实现

1. 真实个体影像分割
2. 动态脉搏形变仿真
3. 反问题求解
4. 基于实验数据的参数反演
5. GUI 图形界面
6. 多血管分叉树与微循环网络

## 4. 输入定义

## 4.1 几何输入

输入来自几何配置文件，至少包含：

- profile 名称
- 外轮廓尺寸
- skin 厚度
- fat 厚度
- bone 参数
- artery 参数
- vein 参数
- 体素尺寸

## 4.2 光学输入

输入来自光学参数配置文件，至少包含：

- tissue 名称
- wavelength
- `mua`
- `mus`
- `g`
- `n`

## 4.3 传感器输入

必须支持两类模式：

### Reflectance

- source 半径
- detector 半径
- source-detector separation
- 是否以 artery 投影为中心放置

### Transmittance

- source 半径
- detector 半径
- 掌背两侧对置放置
- lateral offset

## 4.4 仿真输入

每次仿真至少应包含：

- 几何 profile
- 波长
- 模式
- 光子数
- 体素体 `vol`
- 组织光学参数表 `prop`
- source / detector 配置
- 随机种子

## 5. 输出定义

每次仿真至少必须输出：

1. `fluence` 或等价光场输出
2. detector 检测结果
3. 运行配置快照
4. 元数据文件

建议输出：

5. photon trajectory 子样本
6. 截面图
7. 3D 路径图
8. 汇总 CSV

## 6. 功能需求

## 6.1 几何模块

模块职责：

- 从配置文件生成 wrist 体素模型
- 支持 `preterm_wrist` 和 `term_wrist`
- 支持 sweep 覆盖默认参数
- 输出 `numpy.ndarray` 形式的标签体

最低接口建议：

- `build_wrist_volume(profile_name, overrides=None)`
- `validate_geometry(volume, metadata)`
- `save_volume_preview(volume, out_dir)`

## 6.2 光学参数模块

模块职责：

- 按波长装配组织参数表
- 输出可直接喂给 PMCX 的 `prop`
- 支持 tissue label 到参数表的映射

最低接口建议：

- `load_optical_properties(wavelength_nm)`
- `build_prop_table(wavelength_nm, include_vein=False)`

## 6.3 传感器配置模块

模块职责：

- 为反射模式生成 source-detector 布局
- 为透射模式生成 source-detector 布局
- 根据波长选择默认 separation

最低接口建议：

- `build_reflectance_sensor(profile, wavelength_nm, overrides=None)`
- `build_transmittance_sensor(profile, wavelength_nm, overrides=None)`

## 6.4 仿真运行模块

模块职责：

- 组装 PMCX 输入
- 启动单次仿真
- 保存原始输出
- 提供批量运行入口

最低接口建议：

- `run_single_case(case_config)`
- `run_experiment_matrix(experiment_config)`

## 6.5 分析与可视化模块

模块职责：

- 绘制横截面 fluence 图
- 绘制 detector 结果对比图
- 绘制 trajectory 的 3D 简图
- 输出每组实验的简要汇总表

最低接口建议：

- `plot_cross_section(result, axis='z')`
- `plot_detector_summary(results_df)`
- `plot_trajectories(result)`
- `summarize_runs(run_dir)`

## 7. 实验矩阵要求

## 7.1 基础矩阵

基础矩阵至少覆盖：

- geometry profile：`preterm_wrist`、`term_wrist`
- wavelength：`530`、`660`、`940`
- mode：`reflectance`、`transmittance`

共 12 组基础实验。

## 7.2 反射模式扫参

至少对下面参数扫参：

- `530 nm`：separation = `[1, 2, 3, 4] mm`
- `660 nm`：separation = `[2, 3, 4, 5, 6] mm`
- `940 nm`：separation = `[3, 4, 5, 6, 8] mm`

## 7.3 透射模式扫参

至少对下面参数扫参：

- lateral offset = `[-2, -1, 0, +1, +2] mm`

## 7.4 结构扫参

至少支持下面结构变量：

- skin thickness
- fat thickness
- artery depth
- artery diameter

## 8. 默认运行策略

## 8.1 开发阶段

- voxel size：`0.2 mm`
- 低光子数快速测试
- 每组实验只保存必要结果

## 8.2 正式阶段

- voxel size：`0.1 mm`
- 提高光子数
- 保留完整元数据
- 对关键组合保存 trajectory 子样本

## 9. 目录结构要求

建议 CodeX 按下面结构组织项目：

```text
neoptics/
├─ configs/
│  ├─ geometry_profiles.yaml
│  ├─ optics_tissue.yaml
│  ├─ optics_blood.yaml
│  ├─ sensor_defaults.yaml
│  └─ experiments/
├─ src/
│  ├─ geometry/
│  ├─ optics/
│  ├─ sensors/
│  ├─ simulation/
│  ├─ analysis/
│  └─ visualization/
├─ scripts/
├─ outputs/
├─ tests/
└─ README.md
```

## 10. 非功能需求

1. 代码必须参数化，不能把关键数值硬编码在核心逻辑中。
2. 每次仿真必须保存配置快照。
3. 同一配置重复运行时应支持固定随机种子。
4. 所有输出文件必须带有可追溯的 case id。
5. 批量实验必须允许断点续跑。
6. 可视化脚本必须能脱离 notebook 独立运行。

## 11. 验收标准

## 11.1 最低验收

满足下面条件即通过：

1. 可以生成 `preterm_wrist` 与 `term_wrist` 两个体素模型。
2. 可以分别运行 530/660/940 nm 的单次仿真。
3. 可以分别运行 reflectance 与 transmittance 模式。
4. 可以完成 12 组基础实验并保存结果。
5. 可以输出至少一张横截面 fluence 图。
6. 可以输出至少一张 detector 结果汇总图。
7. 可以通过配置修改 artery depth 和 separation 后重新运行。

## 11.2 推荐验收

如果实现下面内容，则视为优于最低要求：

1. 保存 trajectory 子样本
2. 自动生成实验汇总 CSV
3. 自动生成批量实验报告
4. 支持并行批量运行

## 12. 开发顺序建议

1. 先完成配置文件定义
2. 再完成几何生成器
3. 再完成光学参数装配
4. 再完成传感器配置生成
5. 再完成 PMCX 单次运行脚本
6. 最后完成批量实验与可视化

## 13. 对 CodeX 的直接指令

CodeX 在实现时应遵守：

- 先以配置驱动开发，不要先写死默认值
- 先完成能运行的最小闭环，再扩展 sweep
- 优先保证几何、参数、传感器、仿真、输出五部分之间的数据接口稳定
- 所有图和结果文件都必须能从配置重新生成
