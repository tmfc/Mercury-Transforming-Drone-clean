# 执行控制板 API

本文说明树莓派如何通过 `/dev/ttyAMA1` 上的 **Serial 1 二进制串口协议**与 ESP32-S3 控制器通信。
API 使用带帧边界的字节数据包完成模式切换与行驶控制，不使用字符串指令。

命令标识、字节值、端口和参数按原文保留；以下仅翻译说明。**本次未连接实际控制板验证通信，请在拆除螺旋桨、确保机构安全的条件下调试。**

## 串口配置

| 参数 | 值 |
|------|----|
| 端口 | `/dev/ttyAMA1` |
| 波特率 | **115 200 bps** |
| 数据格式 | 8 N 1：8 位数据、无奇偶校验、1 位停止位 |
| TX / RX 引脚（原表） | ESP32 TX = D6，RX = D7 |
| 逻辑电压 | 3.3 V，直接 UART 连接 |

引脚表按原文保留，实际接线需结合固件和板卡核对；发送端 TX 应接接收端 RX，并共地。

Python 配置示例：

```python
import serial
ser = serial.Serial('/dev/ttyAMA1', 115200, timeout=0.2)
```

## 数据帧结构

双向数据包均使用以下格式：

```text
AA 55 <LEN> <CMD> <PAYLOAD…> <CHK>
```

| 字段 | 含义 |
|------|------|
| `AA 55` | 同步帧头 |
| `<LEN>` | 载荷长度，加上 CMD 所占的 1 字节 |
| `<CMD>` | 命令编号 |
| `<PAYLOAD>` | 对应命令的数据 |
| `<CHK>` | 从 `<LEN>` 到最后一个载荷字节的逐字节异或（XOR） |

示例：`AA 55 01 02 03` 表示 `STOP_ALL`，长度为 1、命令为 `0x02`、校验字节为 `0x03`。

## 命令表：树莓派 → ESP32

| 命令编号（十六进制） | 标识 | 载荷 | 说明 |
|----------------------|------|------|------|
| `0x01` | **MODE_SET** | `u8 mode`：0 NONE、1 CAR、2 DRONE | 切换至 CAR／DRONE 时启动约 10 秒的物理变形 |
| `0x02` | **STOP_ALL** | 无 | 立即停止全部电机 |
| `0x03` | **DRIVE_F** | `u8 pct (0-100)` | 前进，仅限 CAR 模式 |
| `0x04` | **DRIVE_B** | `u8 pct (0-100)` | 后退 |
| `0x05` | **DRIVE_L** | `u8 pct (0-100)` | 向左行驶 |
| `0x06` | **DRIVE_R** | `u8 pct (0-100)` | 向右行驶 |
| `0x07` | **DRIVE_MIX** | `i8 left, i8 right`，范围 -100..100 | 左右轮混合差速控制 |
| `0x08` | **TURNMODE** | `u8 mode`：0 SAME、1 TANK | 可选转向方式 |
| `0x09` | **DMAX_SET** | `u16 delta_us (LE)` | 舵机行程范围 200–500 µs，采用小端字节序 |
| `0x0A` | **STATUS_Q** | 无 | 请求当前状态帧 |

`u8`、`i8`、`u16` 分别表示无符号 8 位、有符号 8 位、无符号 16 位整数；模式标识 NONE／CAR／DRONE 分别表示无模式、车模式、无人机模式，SAME／TANK 为原协议的转向方式标识。

## 响应：ESP32 → 树莓派

| 类型 | 命令编号 | 载荷 | 含义 |
|------|----------|------|------|
| **ACK** | `0x80` | `0x01` | 执行成功 |
| **ERR** | `0x81` | `u8 code` | 1 BadArg：参数错误；2 BadMode：模式错误；3 NotInCar：不在车模式；4 Unknown：未知命令 |
| **STATUS** | `0x82` | `mode u8 active u8 turn u8 dmax u16 reserved u8` | 6 字节状态载荷 |

所有响应均使用相同的 `AA 55 <LEN> <CMD> … <CHK>` 格式。状态字段名保持原样，依次为模式、活动状态、转向方式、最大脉宽变化量和保留字节。

## 指令间隔建议

| 命令类型 | 发送下一条指令前的建议等待时间 |
|----------|--------------------------------|
| `MODE_SET`（CAR／DRONE） | 约 10 秒，对应物理变形时长 |
| 行驶命令（`F/B/L/R/MIX`） | 等待运动完成，通常为 2–3 秒 |
| `STOP_ALL`／`STATUS_Q` | 0.1 秒 |

## Python 使用示例

示例会切换模式并驱动机构，不能在未确认安全的实机上直接运行。

```python
import serial, struct, time
ser = serial.Serial('/dev/ttyAMA1', 115200, timeout=0.2)

def frame(cmd, payload=b''):
    body = bytes([len(payload)+1, cmd]) + payload
    chk = 0
    for x in body: chk ^= x
    return b'\xAA\x55' + body + bytes([chk])

def send(cmd, payload=b'', wait=0.0, label=''):
    print(f"发送：{label or hex(cmd)}")
    ser.write(frame(cmd, payload))
    resp = ser.read(64)
    if resp: print("接收：", resp.hex(' '))
    else:    print("接收：（无响应）")
    time.sleep(wait)

# 示例操作顺序
send(0x01, bytes([1]), 0.1, "切换至车模式（MODE CAR）")
print("等待 10 秒完成变形……")
time.sleep(10)

send(0x03, bytes([50]), 0.1, "以 50% 指令前进（DRIVE_F）")
time.sleep(3)
send(0x02, b'', 0.1, "停止全部电机（STOP_ALL）")

payload = struct.pack('bb', -30, 60)
send(0x07, payload, 0.1, "混合差速（DRIVE_MIX -30,+60）")
time.sleep(2)
send(0x02, b'', 0.1, "停止全部电机（STOP_ALL）")

send(0x01, bytes([2]), 0.1, "切换至无人机模式（MODE DRONE）")
time.sleep(10)
send(0x0A, b'', 0.2, "查询状态（STATUS_Q）")
```

## 十六进制速查：原文示例，需核对校验字节

**原表部分校验字节与上文 XOR 规则不一致，以下字节原样保留供核对，不应直接复制发送。** 例如 MODE CAR 的 `02 XOR 01 XOR 01` 为 `02`，而原表示例末字节为 `03`。请通过上面的 `frame()` 生成报文，并与实际固件核对；本次翻译没有改动协议或固件。

| 操作 | 原文数据帧 |
|------|------------|
| 车模式（MODE CAR） | `AA 55 02 01 01 03` |
| 停止全部电机（STOP_ALL） | `AA 55 01 02 03` |
| 50% 前进指令（DRIVE F） | `AA 55 02 03 32 31` |
| 混合差速（-30,+60） | `AA 55 03 07 E2 3C 18` |
| 查询状态（STATUS_Q） | `AA 55 01 0A 0B` |

## 调试提示

- 可用 `minicom` 或 `screen /dev/ttyAMA1 115200` 检查串口字节。
- 有效数据帧均以 `AA 55` 开始。
- `0x80` ACK 表示成功；`0x81` ERR 表示需检查载荷中的错误码。
- 无响应时，先核对共地、串口参数及 TX／RX 是否交叉连接。

**作者：** Mercurius Robotics  
**用途：** 在树莓派与 ESP32 差速驱动控制器之间建立高效串口桥接。
