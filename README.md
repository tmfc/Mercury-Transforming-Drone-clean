# MERCURY - TRANSFORMING DRONE
<!-- Hardware / Platform -->
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=flat&logo=raspberry-pi&logoColor=white)
![ArduPilot](https://img.shields.io/badge/ArduPilot-025930?style=flat&logo=ardupilot&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-E7352C?style=flat&logo=espressif&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=flat&logo=threedotjs&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=flat&logo=leaflet&logoColor=white)

![Mercury Banner](Media/Banner.png)

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/mercuriustech)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/c/MercuriusTech)
[![Follow on X](https://img.shields.io/badge/Follow%20%40L42ARO-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/L42ARO)
[![Discord](https://img.shields.io/badge/Join%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ZudrWv6E)


## Quick Index

- [Demo](#demo)
- [Features](#features)
- [Folder Structure](#folder-structure)
- [Bill of Materials](#bill-of-materials)
- [CAD Files](#cad-files)
- [Software Setup](#software-setup)

## Demo

[![Mercury Demo](https://img.youtube.com/vi/DZhdSxqXiKo/maxresdefault.jpg)](https://youtu.be/DZhdSxqXiKo)

## Features

<table width="100%">
  <tr>
    <td width="50%" align="center"><b>Inner Payload Bay (1 kg)</b></td>
    <td width="50%" align="center"><b>Simple Transformation Mechanism</b></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="Media/InnerPayload 2.png" alt="Inner Payload Bay" width="100%"/></td>
    <td width="50%" align="center"><img src="Media/LinearActuators.png" alt="Simple Transformation Mechanism" width="100%"/></td>
  </tr>
</table>

<table width="100%">
  <tr>
    <td width="50%" align="center"><b>RGB + Depth + Thermal Cameras</b></td>
    <td width="50%" align="center"><b>Ardupilot + GPS</b></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="Media/Sensors.jpg" alt="RGB + Depth + Thermal Cameras" width="100%"/></td>
    <td width="50%" align="center"><img src="Media/TopDownDrone.png" alt="Ardupilot + GPS" width="100%"/></td>
  </tr>
</table>

<table width="100%">
  <tr>
    <td width="50%" align="center"><b>Wheel + Prop Guard</b></td>
    <td width="50%" align="center"><b>Mobile App</b></td>
  </tr>
  <tr>
    <td width="50%" align="center"><img src="Media/WheelProp.png" alt="Wheel + Prop Guard" width="100%"/></td>
    <td width="50%" align="center"><img src="Media/MobileApp.png" alt="Mobile App" width="100%"/></td>
  </tr>
</table>

## Folder Structure
- **STL Files:** all the required stl files for the drone assembly
- **Autonomy Software:** all the required software for the drone autonomy
- **PCB Files:** all the gerber files for the drone PCBs

## Bill of Materials

| Hardware | Units | Link |
|----------|-------|------|
| 120N Linear Actuator 1.2" | 2 | [Buy](https://a.co/d/f1gvmVA) |
| 8 inch propellers | 4 | [Buy](https://a.co/d/bCJhVNM) |
| BLDC Motor (A2812 2812 900KV) | 4 | [Buy](https://a.co/d/0YZLBnR) |
| Raspberry Pi 5 | 1 | [Buy](https://a.co/d/0e89eMiw) |
| Mobile Data Dongle | 1 | [Buy](https://a.co/d/clkxkL8) |
| Lipo Battery (3S 2200mah) | 2 | [Buy](https://a.co/d/04b29lgE) |
| Screws (3mm x 10mm) | 10 | ACE Hardware |
| Screws (3mm x 30mm) | 20 | ACE Hardware |
| Screws (3mm x 50mm) | 10 | ACE Hardware |
| CF 30 cm x 30 cm (for frame) | 2 | [Buy](https://a.co/d/0dzbtn5p) |
| 8 awg cable | 1 | [Buy](https://www.amazon.com/dp/B07B8N6751) |
| T Plug Pairs | 2 | [Buy](https://www.amazon.com/dp/B01C8NWJ78) |
| XT60 Male & Female | 1 | [Buy](https://www.amazon.com/dp/B0CMM1BBDQ) |
| IMU (MPU 9250) | 2 | [Buy](https://www.amazon.com/dp/B01I1J0Z7Y) |
| TOF Camera | 1 | [Buy](https://www.amazon.com/dp/B0BRB12W7Y) |
| ESP32S3 | 1 | [Buy](https://a.co/d/0fMawJYb) |
| USB Webcam | 1 | [Buy](https://a.co/d/dZ3TK0W) |
| Buck Converter | 3 | [Buy](https://a.co/d/iBVBORv) |
| Radiolink R8XM | 1 | [Buy](https://www.amazon.com/dp/B0BCPDLWXZ) |
| DRV8871 H Bridge | 2 | [Buy](https://a.co/d/iBVBORv) |
| Cube + Flight Controller | 1 | [Buy](https://a.co/d/19FUWXO) |
| SEQURE 4in1 ESC 70A | 1 | [Buy](https://a.co/d/5X12oWn) |
| Custom PCBs | 3 | EasyEDA |
| BLDC Motor 140KV (for driving) | 2 | [Buy](https://a.co/d/iKZayiN) |
| Optical Flow MTF-01 | 1 | [Buy](https://www.ewingaerospace.com/products/ewing-aerospace-h7-flight-controller-ndaa-compliant-and-blueuas) |
| Thermal Camera | 1 | [Buy](https://a.co/d/dZ3TK0W) |
| Bidirectional ESC 50A (for driving) | 2 | [Buy](https://a.co/d/00C138fG) |

## CAD Files

![Mercury CAD](Media/CAD.png)

The STL files are available to download in the [STL Files](STL%20Files) folder. If STL files aren't good enough feel free to [JOIN OUR PATERON](https://www.patreon.com/c/MercuriusTech) for access to the full CAD project as well as SLDPRT and STEP files.

| Name | Qty | Material | Density |
|------|-----|----------|---------|
| [Arm - Left](STL%20Files/Arm%20-%20Left.stl) | 1 | Black PLA-CF | 10% |
| [Arm - Right](STL%20Files/Arm%20-%20Right.stl) | 1 | Black PLA-CF | 10% |
| [BLDC Holder - Left](STL%20Files/BLDC%20Holder%20-%20Left.stl) | 1 | Black PLA-CF | 10% |
| [BLDC Holder - Right](STL%20Files/BLDC%20Holder%20-%20Right.stl) | 1 | Black PLA-CF | 10% |
| [CargoBay - Base](STL%20Files/CargoBay%20-%20Base.stl) | 1 | Black PLA-CF | 10% |
| [CargoBay - Battery Holder 1](STL%20Files/CargoBay%20-%20Battery%20Holder%201.stl) | 1 | Black PLA-CF | 10% |
| [CargoBay - Battery Holder 2](STL%20Files/CargoBay%20-%20Battery%20Holder%202.stl) | 1 | Black PLA-CF | 10% |
| [CargoBay - Battery Holder 3](STL%20Files/CargoBay%20-%20Battery%20Holder%203.stl) | 1 | Black PLA-CF | 10% |
| [CargoBay - Battery Holder 4](STL%20Files/CargoBay%20-%20Battery%20Holder%204.stl) | 1 | Black PLA-CF | 10% |
| [CargoBay - Cover](STL%20Files/CargoBay%20-%20Cover.stl) | 1 | White Aero PLA | 0–5% |
| [Cover - Base](STL%20Files/Cover%20-%20Base.stl) | 1 | Black PLA-CF | 10% |
| [Cover Out - Bottom](STL%20Files/Cover%20Out%20-%20Bottom.stl) | 1 | Red PLA | 0–5% |
| [Cover Out - Front Name](STL%20Files/Cover%20Out%20-%20Front%20Name.stl) | 1 | Red PLA | 0–5% |
| [Cover Out - Front Sensors](STL%20Files/Cover%20Out%20-%20Front%20Sensors.stl) | 1 | Red PLA | 0–5% |
| [Cover Out - Front](STL%20Files/Cover%20Out%20-%20Front.stl) | 1 | Red PLA | 0–5% |
| [Cover Out - Rear](STL%20Files/Cover%20Out%20-%20Rear.stl) | 1 | Red PLA | 0–5% |
| [Cover Out - Top Front](STL%20Files/Cover%20Out%20-%20Top%20Front.stl) | 1 | Red PLA | 0–5% |
| [Cover Out - Top Rear](STL%20Files/Cover%20Out%20-%20Top%20Rear.stl) | 1 | Red PLA | 0–5% |
| [Drone Motor Holder](STL%20Files/Drone%20Motor%20Holder.stl) | 1 | Black PLA-CF | 10% |
| [Gear - Central](STL%20Files/Gear%20-%20Central.stl) | 2 | Black PLA-CF | 10% |
| [Gear - Driving](STL%20Files/Gear%20-%20Driving.stl) | 2 | Black PLA-CF | 10% |
| [Gear - Peripheral](STL%20Files/Gear%20-%20Peripheral.stl) | 2 | Black PLA-CF | 10% |
| [Linear Actuator Holder](STL%20Files/Linear%20Actuator%20Holder.stl) | 2 | Black PLA-CF | 10% |
| [ShoulderMount - Front](STL%20Files/ShoulderMount%20-%20Front.stl) | 1 | Black PLA-CF | 10% |
| [ShoulderMount - Rear](STL%20Files/ShoulderMount%20-%20Rear.stl) | 1 | Black PLA-CF | 10% |
| [Wheel - Left](STL%20Files/Wheel%20-%20Left.stl) | 2 | Black PLA-CF | 10% |
| [Wheel - Right](STL%20Files/Wheel%20-%20Right.stl) | 2 | Black PLA-CF | 10% |
| [Frame Side Blueprint](STL%20Files/Frame%20Side%20Blueprint.pdf) | 2 | Carbon Fiber Sheet | N/A |

## 简化双片电子舱（本地改型）

此改型取消货物空间、货舱门及独立电池托架，将中央电子舱整合为 **下舱体＋上盖** 两个打印件。原 STL 保留为尺寸依据；新文件位于 [`Electronics Bay`](Electronics%20Bay)，不改变机臂、肩部安装座、齿轮或侧碳板。

### 打印文件

| 文件 | 数量 | 打印包络，宽 X × 长 Y × 高 Z（mm） |
|------|------|---------------------------------|
| [下舱体 STL](Electronics%20Bay/Electronics_Bay_Lower.stl) | 1 | 180.8 × 201.2 × 45.3 |
| [上盖 STL](Electronics%20Bay/Electronics_Bay_Upper.stl) | 1 | 180.8 × 201.2 × 17.5 |

装配外包络为 **180.8 × 201.2 × 60.3 mm**。上盖打印高度包含向下插入下壳的定位裙边，不能直接与下壳打印高度相加。另提供 [STEP 装配模型](Electronics%20Bay/Electronics_Bay_Assembly.step)、[外观及爆炸预览](Electronics%20Bay/Electronics_Bay_Preview.png)、[参数化生成脚本](Electronics%20Bay/generate_bay.py) 和 [网格验证数据](Electronics%20Bay/Validation.json)。

### 接口与内部空间

- 主壳宽 164.8 mm，安装座最外侧宽 180.8 mm；壁、底板、顶板均为 3 mm。下部主腔净宽 × 净长约 158.8 × 195.2 mm；扣合处最小开口约 147.4 × 183.8 mm，圆角和局部安装凸台会占用空间。
- 内置 6 mm 高电子板安装柱：一组 58 × 49 mm 孔距用于 Raspberry Pi 5，一组 30.5 × 30.5 mm 用于匹配孔距的飞控板。柱上为直径 2.2 mm、深 4.2 mm 的盲导孔，需按实际紧固件加工；不是已成型螺纹。30.5 mm 孔距不代表兼容原 BOM 中 Cube 的所有载板。安装柱顶面至上盖内顶约 48.3 mm，需计入板厚、插头及线缆弯曲。
- 从原 `CargoBay - Base.stl` 的两侧截面测得并保留 8 个水平安装孔轴线：原坐标 Y 为 ±97.1、±26 mm；对应 Z 为 −48.65、−48.15 mm。新装配坐标等于原坐标加 `(0, 0, 60.15)` mm。孔位测量偏差小于 0.01 mm；孔径改为热熔螺母安装孔，不能照搬原来的穿透螺钉长度。
- 侧面中央 `|Y| < 20 mm` 区域没有向外伸出的安装座，主壳相对原侧面安装平面内收 8 mm；这只是几何避让设计，不等于全行程机构无干涉证明。
- 后壁有两个直径 12.2 mm 的通孔及 6 mm 厚局部加强台，用于匹配安装尺寸的 M12 防水格兰头；不用的孔必须安装带密封件的堵头。它们不是打印螺纹。

### 打印与装配

1. STL 单位为 **mm**，按 **100%** 导入；至少需要约 200 × 220 mm 的有效平台，启用 brim 时再留出边距。两个 STL 已各自摆好打印方向：下壳底朝下，上盖外顶面朝下、内腔朝上。STEP 中则是实际装配方向。
2. 建议 PETG 或 ASA、0.4 mm 喷嘴、0.2 mm 层高、至少 5 道外墙、至少 6 层顶底面、25–35% 填充；不要套用原货舱的 0–5% 填充设置。大平面注意翘曲。ASA 需要合适的封闭、排风条件。侧面安装座和上盖螺钉柱已延伸到底面；小横孔、内部加强台是否需要局部支撑由切片预览决定，密封槽和内腔避免无法取出的支撑。
3. 需要 **16 个 M3 热熔螺母**：8 个用于上盖，8 个用于侧机架。模型预留直径 4.2 mm、深 5.2 mm 的安装孔；选择与此预留孔匹配、长度不超过 5 mm 的热熔螺母，不能仅按 M3 内螺纹规格购买。先校准打印孔径。侧面孔为盲孔，禁止钻穿进入舱内。
4. 上盖使用 8 颗 M3 × 20 mm 圆柱头内六角螺钉，头径不超过 5.8 mm、头高不超过 3.2 mm；不加额外厚垫片。侧机架若为 2 mm 厚板，可从 M3 × 8 mm 试装，按实测板厚确认有效长度，避免盲孔顶底。电子板使用与安装柱匹配的紧固件，不得穿透舱底。
5. 周向密封槽宽 **2.4 mm**、深 **1.3 mm**；使用直径 **2 mm** 硅胶密封绳，中心线周长约 699.4 mm，建议备约 720 mm 后按实物裁切并可靠接合。定位裙边单侧名义间隙 0.3 mm；限位柱形成 0.3 mm 合盖间隙，密封绳名义压缩率 20%。不能为了消除这条设计间隙继续强拧螺钉。
6. 先空壳试装、缓慢手动检查变形全行程，再装电子器件。接缝、线缆口和打印层纹均需单独验证密封；如需表面封孔，涂层厚度也要计入配合间隙。

### 已验证与边界

已实际运行生成器：两件均为单连通、封闭且法向一致的实体网格；CAD 布尔与导出 STL 布尔检查的装配体积干涉均为 0 mm³。另以 0.2 mm 间隔检查下壳 226 个、上盖 87 个水平截面，轮廓均闭合；STEP 回读后的 34 个材料／空腔探针验证了侧面盲孔隔离壁、电子板盲孔底部、线缆孔和中部避让。这里的“封闭网格”不代表实物防水。

**未进行实物打印、整机变形运动检查、承载试验、热测试或浸水试验，也未针对特定打印机生成 G-code。** 原项目展示的是飞行／轮式变形平台，并非经验证的水密两栖平台。本电子舱不是整机浮体或承力侧机架的替代品；原外饰板、电池支架及传感器面板不再承诺匹配。电池若仍使用原货舱托架，需要另行安排固定位置，不能放任其在电子舱内移动。密闭电子舱的散热、整机重心、浮力和变形空间需在实物上重新评估，水密测试应先用无电子器件的空舱进行。

重新生成（Python 3.12+，从项目根目录）：

```bash
uv venv --python 3.12 /tmp/mercury-cad
uv pip install --python /tmp/mercury-cad/bin/python cadquery==2.8.0 trimesh manifold3d vtk scipy
/tmp/mercury-cad/bin/python "Electronics Bay/generate_bay.py"
```

## Software Setup

To use the software as it is, upload the Autonomy Software folder to a Raspberry Pi 5, using your preferred SCP method. For beginners we recommend [WinSCP](https://winscp.net/eng/download.php).

Inside the folder in the raspberry pi create a virtual environment and install the dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You must run both the Mavproxy Bridge to interface with the flight controller as well as the main software powering the rest of the robot. For that run in two separate temrinals the scripts:

```bash
start_mavproxy.sh
```
```bash
run.sh
```
In the terminal you should see the IP addres to be able to control the robot, if you're connected to the same network just copy paste that on your browser.

If you would like to be able to control it from different networks and at long distances we recommend you setup [Tailscale](https://tailscale.com/) on your devices.

For more convenience you can setup these scripts to run automatically on startup, and then use other scripts like `restarter.sh` or `killer.sh` to manage them.

## 🧑‍💻 Official Codebase Core Contributors and Maintainers

<table>
  <tr>
    <td align="center">
      <a href="https://x.com/L42ARO">
        <img src="https://images.weserv.nl/?url=https://pbs.twimg.com/profile_images/1995738246702399488/ZSnjIfgK_400x400.jpg&h=100&w=100&fit=cover&mask=circle&maxage=7d" width="100px;" alt=""/>
      </a>
      <br />
      <sub><b>Alvaro L</b></sub>
    </td>
    <td align="center">
      <a href="https://x.com/pericleshimself">
        <img src="https://images.weserv.nl/?url=https://pbs.twimg.com/profile_images/1976158790861963264/uqXdzZBm_400x400.jpg&h=100&w=100&fit=cover&mask=circle&maxage=7d" width="100px;" alt=""/>
      </a>
      <br />
      <sub><b>Connor Raymer</b></sub>
    </td>
  </tr>
</table>

*Join our Pateron for full access to the CAD project as well as .SLDPRT & .STEP formats*


[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/mercuriustech)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/c/MercuriusTech)

*If you have any questions or need support, feel free to join our Discord server*

[![Discord](https://img.shields.io/badge/Join%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ZudrWv6E)