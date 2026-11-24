# Mercury 配送与远程操控软件

本目录用于 Mercury 机器人的配送作业与远程操控。

- 安装、虚拟环境及运行入口见[项目中文总说明](../README.md#软件安装与运行)。
- [遥控前端开发说明](TeleopFrontendDev/README.md)介绍开发、构建和测试脚本。
- [执行控制板串口协议](ExperimentDev/SerialTests/README.md)说明树莓派与 ESP32-S3 之间的二进制通信。
- [MAVLink 命令参考](mavlink_command.txt)、[ArduPilot 配平记录](ardupilot_trim.txt)及[硬件连接示意图](schematics.drawio)保留原参数，补充中文说明。

原图中的电源、电机和电池规格未在本次翻译中重新验证，不应将原理示意图直接作为最终接线或采购依据。

## STM32 履带电机：PX4 UART4 上的 CH6 / CH12 双路调速

见[双路减速电机台架指南](STM32TrackMotor/README.md)：电机和飞控接线、QGroundControl 参数与遥控校准、STM32 烧录、联调验收和实测边界。