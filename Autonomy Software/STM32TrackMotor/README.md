# PX4 UART4 → STM32：CH6 / CH12 双路减速电机台架指南

本指南对应 MicoAir H743 V2（本次读回 **PX4 1.14.3**）、正点原子 M144Z-M4 Mini Board（STM32F407ZGT6）和 JIS-GM144-1408A（铭牌 DC 14.4 V）无刷减速电机。STM32 固件独立运行，不替换原项目的 ESP32-S3 执行板。旧的 USB 串口点动和电机特性见[单电机台架记录](../../STM32-Motor-Control.md)。

## 电机及 STM32 接线

先断开所有电机电源。以下接法仅适用于已经验证的电机，或确认兼容 **3.3 V 控制、低电平有效 PWM、高电平使能 BRK** 的同类电机。不同型号须先查铭牌、控制电平和极性。

| 电机端 | 第一路：CH6 | 第二路：CH12 |
| --- | --- | --- |
| 电源 `+` / `−` | 独立 14.4 V 电源正、负极（按本电机铭牌） | 按第二台铭牌接其电源正、负极 |
| `PWM` | `PB10`，`JP2-28` | `PA15`，`JP2-27` |
| `BRK` / `BKR` | `PB11`，`JP2-29` | `PC0`，`JP2-15` |
| `CW/CCW` | `PB12`，`JP1-22` | `PC1`，`JP2-16` |

以板上 1 脚标记和[开发板原理图](https://raw.githubusercontent.com/openedv/M144Z-M4-Mini-Board-STM32F407/master/1_docs/1_sch/ATK-DNM144Z-M4_STM32F407.pdf)为准。电机负极直接回电源，再单独引信号地到 STM32 `GND`；杜邦线只走信号，不走电机电流。STM32 可由板载 `USB UART` 口供电，**不得把 14.4 V 接进开发板**。不要把 STM32 输出和原电机控制板输出并接。使用限流电源和可立即断开的电源开关；带电机前要确认 STM32 复位、掉电或断线时，电机侧也有可靠的 `BRK` 低电平默认状态，不能仅靠固件保证。

`BRK` 高电平允许驱动，低电平停止。`CW/CCW` 低为逻辑正转，高为逻辑反转；轴从哪一面看、如何安装会影响实际转向。PWM 频率为 1 kHz，速度指令取遥控值的绝对值，表示**低电平占比，不是实测转速**。例如 `±60` 都给 60% 低电平占比；`±100` 都是 PWM 持续低电平，因此不能把 PWM 拉低当作停机。

## 飞控与 STM32 接线

使用 [MicoAir H743 V2 的 UART4](https://micoair.com/api/media/file/docs/2026/10/image-a75f473315-fdb7573d62.webp)，在这块飞控的 PX4 中叫 **TELEM2**。不是飞控的 PWM 电机输出，也不是把 CH6 或 CH12 分别接到飞控的第 6 或第 12 个输出。两个通道都由一根 MAVLink 串口信号线传输。

| 飞控 UART4 针脚（从 `GND` 端开始） | 接法 |
| --- | --- |
| 1：`GND` | 接 STM32 `GND`，与电机信号地共地 |
| 2：`5V` | **不接**，不用它给 STM32 供电 |
| 3：`TX4` | 接 STM32 `PA1`（`UART4_RX`，3.3 V 逻辑） |
| 4：`RX4` | **不接**；STM32 只接收，不向飞控回发 |

先对照针脚再认线色。若线束确实从 `GND` 端依次是黑、红、黄、绿，则接黑线和黄线，另两根分别绝缘。配置时用飞控 USB-C 连电脑；STM32 的 USB UART 用于供电或烧录，是另一条连接。配置保存后，飞控、接收机和 STM32 正常供电即可运行，不需要电脑保持连接。

## QGroundControl 配置（PX4）

1. 保持电机断电、飞控不解锁，用 USB-C 连接飞控。在桌面版 QGroundControl（QGC）打开 [**Vehicle Setup → Parameters**](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/setup_view/parameters.html)，可先用 **Tools → Save to file** 备份参数。
2. 搜索并逐个保存下表参数。若 `SER_TEL2_BAUD` 尚未出现，先分配 TELEM2 并重启，再设置波特率并重启。完成后重新连接并读回参数，不使用 ArduPilot 的 `SERIAL4_*` 或舵机输出映射。

   | 参数 | 本台架值 | 用途 |
   | --- | ---: | --- |
   | `MAV_1_CONFIG` | `102`（TELEM 2） | 在物理 UART4 上启用 MAVLink |
   | `MAV_1_MODE` | `2`（Onboard） | 主动发送 `RC_CHANNELS` 和 `SYS_STATUS` |
   | `MAV_1_FLOW_CTRL` | `0`（Force off） | 两线接法不使用 RTS/CTS |
   | `MAV_1_RATE` | `10000` | 本实例发送速率上限，单位字节/秒 |
   | `MAV_1_FORWARD` | `0` | 不转发其他 MAVLink 链路 |
   | `SER_TEL2_BAUD` | `115200` | 与 STM32 的 115200、8N1 匹配 |
   | `MAV_SYS_ID` | `1` | 固件接受系统 ID `1`、组件 ID `1` 的无签名 MAVLink 1/2 |
   | `RC_MAP_FLTMODE` | `5` | 保留 CH5 切换飞行模式；STM32 不读取 CH5 |

3. 在 [**Vehicle Setup → Radio**](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/setup_view/radio.html)确认遥控器已绑定。若需重新校准，按 QGC 提示移动主摇杆，并让 CH6 和 CH12 各自走完整行程；确认这两路没有兼作飞行模式、安全开关或其他动作。不需要把它们映射成 PX4 的 AUX 输出。
4. 在 [**Analyze Tools → MAVLink Inspector**](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/analyze_view/mavlink_inspector.html)展开 `RC_CHANNELS`，分别看 `chan6_raw`、`chan12_raw`。本台架两路校准均为 `1065 / 1499 / 1933 µs`；低端映射 `+100`、高端映射 `−100`。回中读数应在 `1469–1529 µs` 内。若变更遥控校准，核对实际端点、回中和方向，并同步 [`rc_drive.h`](rc_drive.h) 后重新构建；固件读的是原始微秒数，不是遥控器显示的百分比，也不会自动读取 PX4 参数。
5. 在 [**Analyze Tools → MAVLink Console**](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/analyze_view/mavlink_console.html)运行 `mavlink status` 和 `mavlink status streams`。从第一条找到 `Onboard`、`115200` 的 TELEM2 实例（本板 `/dev/ttyS3`，不是电脑上的 USB 串口名）。从第二条看该实例括号内的速率：`RC_CHANNELS` 和 `SYS_STATUS` 分别须高于约 2.86 Hz 和 1.25 Hz，并给抖动留余量。USB Inspector 的频率不能代替 UART4 的频率。参见 [PX4 MAVLink 串口配置](https://docs.px4.io/v1.14/en/peripherals/mavlink_peripherals)。

本次 `MAV_1_RATE=0` 时，PX4 报告 TELEM2 的 `SYS_STATUS` 约 1 Hz，不能在 STM32 的 800 ms 时限内持续更新，表现为推杆后 `BRK` 不起。改为 `10000` 并重启后，PX4 报告 `RC_CHANNELS` 约 7.34 Hz、`SYS_STATUS` 约 1.84 Hz。随后从 STM32 的 `PA1` 直接采集 12 秒，解码到 84 帧 `RC_CHANNELS`、21 帧 `SYS_STATUS`，未发现 UART 接收错误。

## 构建、烧录与台架验收

在仓库根目录使用 ARM GNU 工具链构建：

```sh
make -C 'Autonomy Software/STM32TrackMotor'
```

产物是 `Autonomy Software/STM32TrackMotor/build/track-motor.bin`。断开所有电机电源，在 STM32 ROM 烧录模式经板载 USB UART 写入 `0x08000000`，只擦除镜像所在的 Flash 扇区 0。写入后回读比对，将 `BOOT0` 恢复为 `0` 并复位。本次实际使用 Cortex-M4 Clang/LLD 构建、`stm32loader` 烧录，扇区 0 回读校验通过。

1. **先不接电机电源。** 黑表笔接 STM32 `GND`，先用直流档测板上的 `3.3V` 确认量程和共地。CH6 和 CH12 各自回中至少 2 秒，`PB11` 与 `PC0` 都应约为 `0 V`。
2. 只推 CH6，确认 `PB11` 约 `3.3 V` 且 `PC0` 仍约 `0 V`；CH6 回中，`PB11` 应降到约 `0 V`。只推 CH12，确认 `PC0` 约 `3.3 V` 且 `PB11` 仍约 `0 V`；CH12 回中，`PC0` 应降到约 `0 V`。再在电机端的 `BRK` 线上复核对应电平，避免量错排针或只验证到板端。
3. 两路都发出运行指令时，关闭遥控器，确认两个 `BRK` 都变低。恢复后保持通道偏离中位，两个 `BRK` 都不得自行拉高；分别回中后才允许各自重新使能。再用同样流程单独测试断开飞控 `TX4` 信号线。接收机不能在失联后隐瞒故障并保持最后的运动指令。固件要求三条连续、时间戳前进的中位消息；CH6/CH12 单路无效只停止该路，串口错误、接收机不健康、遥控消息超过 350 ms 或健康消息超过 800 ms 未更新则停止两路。上述是 STM32 超时，遥控器到飞控的失联检测另外有延迟。
4. 固定电机、拆下履带和螺旋桨，确认可立即断电后，两个通道回中再给电机供电。从低速开始分别验证正转、回中停机、反转和比例调速。换向先拉低 `BRK`，由停机指令起计 **1 秒**才切方向，再等 **100 ms**才使能；在中位停留的时间计入这 1 秒。该设定从最初约 4.1 秒缩短到约 1.1 秒，**不是零速检测**。需要连续换向前，先测预期最高测试转速下两个方向的停稳时间，确认均明显短于 1 秒；带履带或负载改变后必须重测。

## 本次验证结果与边界

| 项目 | 已验证和未验证的范围 |
| --- | --- |
| STM32 点动 | 旧点动固件输出 50% PWM，串口记录 2.01 秒后撤销驱动，现场观察到电机转动后停止。 |
| CH6 实机 | 单台电机空载正反转、方向、比例调速、回中停机及失联停机通过。`PB11` 万用表一度读到 `0 V`，与 STM32 数字回读不一致；后来在 STM32 裸针与电机 `BRK` 端都测到高电平。 |
| CH12 实机 | 将同一台电机移到第二路，确认能正反转；现场确认缩短后的换向延迟可接受。未实测两台电机同时带电运行，也未做带履带、带载测试。 |
| 双路固件 | ARM 仿真验证了两路独立解锁、同时驱动、一侧换向不影响另一侧和共享链路失联停机，并验证两路 1.1 秒换向时序。 |
| 满杆转速不同 | CH12 正转满杆 `1065 µs`、反转满杆 `1933 µs`，两端均给 100% 有效 PWM；断电测量电机端两边均约 `0 V`。未发现固件给正转限速。未比较两方向带电运行时的端电压、电流或实测转速，不能据此确定是供电、内置驱动还是减速机构。 |

设计沿用 PX4 UART4；早期的 CH5 开关/PWM 输入试案不在当前固件中。保留 CH5 给飞行模式，改用 CH6 连续调速，校准方向后再加独立的 CH12。
