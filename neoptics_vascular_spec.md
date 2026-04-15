# NeoOptics 血管结构与参数说明文档

## 1. 文档目的

本文档用于固定 NeoOptics 项目第一阶段的血管结构建模边界、默认几何参数、默认血液光学参数以及必须支持的扫参范围。

本文档的作用不是给出最终生理解剖真值，而是提供一套可直接编码的 **v1 工程基线**，供 CodeX 基于该基线实现：

- 体素化几何生成器
- 血管结构生成器
- 波长相关的血液参数加载器
- MCX/PMCX 仿真脚本
- 结果可视化与批量实验脚本

## 2. 适用范围

当前版本仅覆盖：

- 新生儿 wrist-scale 模型
- 两类 profile：`preterm_wrist`、`term_wrist`
- 两类血管：`arterial_blood`、`venous_blood_optional`
- 三个波长：`530 nm`、`660 nm`、`940 nm`
- 两种工作模式：`reflectance`、`transmittance`

当前版本不覆盖：

- 真实个体超声重建
- 分叉血管树
- 非圆柱血管壁弹性变化
- 脉搏周期内的连续形变场
- 血流动力学求解

## 3. 参数确定原则

### 3.1 文献锚点

几何参数优先锚定到下面几类公开数据：

1. 新生儿/早产儿总体尺寸量级
2. 新生儿前臂直径与皮下脂肪厚度
3. 新生儿前臂皮肤厚度
4. 婴幼儿 distal radial artery 的深度与直径分布

### 3.2 工程默认值

当 wrist 直接测量数据不足时，允许基于文献量级进行工程压缩和简化，但必须满足下面规则：

- 所有默认值必须写入配置文件
- 所有关键尺寸必须可扫参
- 任何“默认值”不能写死在算法代码中
- 体素生成器必须能够从配置重新生成模型

## 4. 坐标系与标签定义

### 4.1 坐标系

- `x`：左右方向，桡侧为正方向
- `y`：掌侧到背侧方向，掌侧为负方向
- `z`：沿前臂轴向

### 4.2 体素标签

- `0`：air
- `1`：skin
- `2`：fat
- `3`：soft_tissue_or_muscle
- `4`：bone
- `5`：arterial_blood
- `6`：venous_blood_optional

## 5. 血管结构建模定义

## 5.1 动脉

默认目标血管为 **掌侧桡侧的表浅动脉**，按与 distal radial artery 对齐的工程结构处理。

建模方式：

- 形状：圆柱体
- 轴向：沿 `z` 方向延伸
- 截面：圆形
- 介质标签：`arterial_blood`
- 在 v1 中不显式建模血管壁厚度
- 在 v1 中不做脉搏时变半径，只保留静态几何

## 5.2 静脉

静脉为可选背景血管，用于提供非脉动血池背景。

建模方式：

- 形状：圆柱体
- 轴向：沿 `z` 方向延伸
- 截面：圆形
- 介质标签：`venous_blood_optional`
- 默认启用为 `false`

## 5.3 骨组织与血管相对位置

v1 模型中，骨组织只提供几何遮挡和高散射障碍，不承担真实腕骨重建任务。

约束如下：

- 动脉必须位于掌侧浅层
- 动脉必须位于 radius 骨的掌侧附近
- 静脉位于动脉更浅或相近平面，但不与动脉重叠
- 血管中心必须始终位于外轮廓内部，且不与骨组织重叠

## 6. 外轮廓与层状组织定义

## 6.1 外轮廓

横截面使用椭圆近似：

- `width_mm`：左右方向总宽度
- `thickness_mm`：掌背方向总厚度

## 6.2 层状组织关系

从外向内的默认层次为：

1. `skin`
2. `fat`
3. `soft_tissue_or_muscle`
4. `bone`
5. 局部嵌入 `arterial_blood`
6. 可选嵌入 `venous_blood_optional`

说明：

- `skin` 作为总皮肤厚度处理，不再细分表皮与真皮
- `fat` 作为皮下脂肪层
- `soft_tissue_or_muscle` 作为非骨、非脂肪、非血管的主体背景组织

## 7. 默认几何参数

## 7.1 通用参数

| 参数 | 默认值 |
|---|---:|
| voxel_size_mm_debug | 0.2 |
| voxel_size_mm_final | 0.1 |
| domain_x_mm | 32.0 |
| domain_y_mm | 28.0 |
| domain_z_mm | 16.0 |

## 7.2 `preterm_wrist`

| 参数 | 默认值 |
|---|---:|
| outer_width_mm | 18.0 |
| outer_thickness_mm | 15.0 |
| axial_length_mm | 16.0 |
| skin_thickness_mm | 1.0 |
| fat_thickness_mm | 2.8 |
| artery_radius_mm | 0.30 |
| artery_center_x_mm | 3.2 |
| artery_center_y_mm | -5.8 |
| vein_radius_mm | 0.40 |
| vein_center_x_mm | 1.2 |
| vein_center_y_mm | -4.9 |
| radius_bone_center_xy_mm | [3.0, 2.0] |
| radius_bone_semi_axes_mm | [2.0, 1.3] |
| ulna_bone_center_xy_mm | [-3.4, 1.8] |
| ulna_bone_semi_axes_mm | [1.6, 1.1] |

## 7.3 `term_wrist`

| 参数 | 默认值 |
|---|---:|
| outer_width_mm | 21.0 |
| outer_thickness_mm | 17.0 |
| axial_length_mm | 16.0 |
| skin_thickness_mm | 1.0 |
| fat_thickness_mm | 3.2 |
| artery_radius_mm | 0.35 |
| artery_center_x_mm | 3.6 |
| artery_center_y_mm | -6.8 |
| vein_radius_mm | 0.50 |
| vein_center_x_mm | 1.5 |
| vein_center_y_mm | -5.7 |
| radius_bone_center_xy_mm | [3.5, 2.3] |
| radius_bone_semi_axes_mm | [2.3, 1.5] |
| ulna_bone_center_xy_mm | [-4.0, 2.0] |
| ulna_bone_semi_axes_mm | [1.9, 1.3] |

## 8. 血液光学参数定义

## 8.1 波长

必须支持：

- `530 nm`
- `660 nm`
- `940 nm`

## 8.2 参数字段

每个血液介质必须包含：

- `mua`
- `mus`
- `g`
- `n`

单位：

- `mua`：`mm^-1`
- `mus`：`mm^-1`
- `g`：无量纲
- `n`：无量纲

## 8.3 `arterial_blood` 默认值

| wavelength_nm | mua | mus | g | n |
|---|---:|---:|---:|---:|
| 530 | 24.24 | 99.91 | 0.988 | 1.40 |
| 660 | 0.247 | 92.29 | 0.985 | 1.40 |
| 940 | 0.727 | 56.84 | 0.977 | 1.40 |

## 8.4 `venous_blood_optional` 默认值

| wavelength_nm | mua | mus | g | n |
|---|---:|---:|---:|---:|
| 530 | 24.09 | 92.08 | 0.989 | 1.40 |
| 660 | 0.723 | 81.45 | 0.986 | 1.40 |
| 940 | 0.642 | 49.66 | 0.978 | 1.40 |

## 8.5 参数解释

- `530 nm`：浅层敏感波长，主要用于反射模式
- `660 nm`：红光通道，兼顾浅层与中等深度
- `940 nm`：近红外通道，主要用于更深穿透和透射模式
- `arterial_blood`：用于脉动目标血管
- `venous_blood_optional`：用于静态背景血池或静脉

## 9. 必须实现的扫参范围

## 9.1 几何扫参

| 参数 | 默认值 | sweep |
|---|---:|---|
| skin_thickness_mm | 1.0 | [0.8, 1.0, 1.2] |
| fat_thickness_mm_preterm | 2.8 | [2.3, 2.8, 3.2, 3.5] |
| fat_thickness_mm_term | 3.2 | [2.8, 3.2, 3.5, 4.0] |
| artery_diameter_mm_preterm | 0.6 | [0.5, 0.7, 0.9] |
| artery_diameter_mm_term | 0.7 | [0.5, 0.7, 0.9] |
| artery_depth_mm | 1.7 | [1.2, 1.5, 1.7, 2.0] |

## 9.2 血液扫参

v1 不要求连续谱计算，但要求预留参数化能力。

最低要求：

- arterial SO2 允许切换
- venous SO2 允许切换
- 血液参数允许通过配置整体替换

## 10. 对 CodeX 的实现要求

## 10.1 几何生成器

CodeX 必须实现：

- 按 profile 名称生成 3D 体素模型
- 支持 `preterm_wrist` 与 `term_wrist`
- 支持是否启用静脉
- 支持覆盖默认的血管深度、半径与位置
- 支持输出整数标签体 `vol`

## 10.2 约束检查

生成器必须实现：

- 血管不得越界
- 血管不得与骨重叠
- 层厚不得为负
- `skin + fat` 不能超过掌侧到模型中心的距离

## 10.3 配置组织方式

建议拆成：

- `configs/geometry_profiles.yaml`
- `configs/vascular_defaults.yaml`
- `configs/optics_blood.yaml`

## 11. v1 验收条件

满足下面条件即视为通过：

1. 可以从配置生成 `preterm_wrist` 与 `term_wrist` 两个体素模型。
2. 可以启用或关闭静脉。
3. 可以按 530/660/940 nm 载入两类血液光学参数。
4. 可以对 artery depth / diameter 进行扫参。
5. 可以把生成结果直接传给 PMCX/MCX 运行脚本。
