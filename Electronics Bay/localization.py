"""为二维图表和三维预览选择可显示中文的本机字体，不改动模型数据。"""
from functools import lru_cache


@lru_cache(maxsize=1)
def chinese_font_path():
    """返回支持常用中文标注的字体文件；缺少字体时明确报错。"""
    from matplotlib import font_manager, ft2font

    for family in ("Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC",
                   "Microsoft YaHei", "SimHei", "WenQuanYi Zen Hei",
                   "Arial Unicode MS", "Heiti SC"):
        try:
            path = font_manager.findfont(
                font_manager.FontProperties(family=family), fallback_to_default=False)
        except ValueError:
            continue
        font = ft2font.FT2Font(path)
        if all(font.get_char_index(ord(char)) for char in "电子舱肩座螺母装配布局验证中文"):
            return path
    raise RuntimeError("未找到可显示中文的字体。请安装思源黑体或 Noto Sans CJK SC，再重新生成图表。")


def configure_chinese_font():
    """配置 Matplotlib 中文及负号显示，并返回同一字体供 VTK 使用。"""
    import matplotlib
    from matplotlib import font_manager

    path = chinese_font_path()
    matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=path).get_name()
    matplotlib.rcParams["axes.unicode_minus"] = False
    return path
